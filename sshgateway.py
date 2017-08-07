import re
import sys
import pytoml
import crypt
import asyncio
import asyncssh
import argparse
import operator
from functools import reduce
from os.path import expanduser
from collections import namedtuple
__version__ = '0.1.3'
config = {
    'passwords': {},
    'hosts': [],
    'groups': [],
    'permissions': [],
    'listen': '',
    'port': 8022,
    'authorized_client_keys': '~/.ssh/authorized_keys',
    'server_host_keys': ['/etc/ssh/ssh_host_rsa_key'],
    'client_key': '~/.ssh/{}.pem',
    'banner': 'SSH Gateway, welcome {username}!'
}
host_dict = {}
Host = namedtuple('Host', ['name', 'hostname', 'username', 'sshkey', 'proxy'])
Group = namedtuple('Group', ['name', 'users'])
Permission = namedtuple('Permission', ['groups', 'hostnames'])


def can_group_access(group, host):
    for perm in config['permissions']:
        for pattern in perm.hostnames:
            if re.match(pattern, host.name):
                return True
    return False


def can_user_access(username, host):
    for group in config['groups']:
        if username in group.users:
            if can_group_access(group, host):
                return True
    return False


def get_user_hosts(username):
    groups = [group for group in config['groups'] if username in group.users]

    def perm_has_groups(perm):
        return any(g.name in perm.groups for g in groups)

    permissions = filter(perm_has_groups, config['permissions'])
    host_patterns = reduce(operator.add,
                           [perm.hostnames for perm in permissions], [])

    def match(host):
        return any(re.match(pattern, host.name) for pattern in host_patterns)

    return list(filter(match, config['hosts']))


async def handle_client(process):
    username = process.channel.get_extra_info('username')
    process.stdout.write(config['banner'].format(username=username))
    process.stdout.write('\nYou are authorized to login into these servers:\n')
    my_hosts = get_user_hosts(username)
    output = '\n' + ''.join(
        f'{i}) {host.name} {host.username}@{host.hostname}\n'
        for i, host in enumerate(my_hosts)
    )
    while True:
        process.stdout.write(output)
        process.stdout.write('Please enter a server number(q to quit): ')
        process.channel.set_echo(True)
        process.channel.set_line_mode(True)
        line = await process.stdin.readline()
        if not line:
            break
        line = line.strip()
        if line in ('q', 'quit'):
            break
        try:
            host = my_hosts[int(line)]
        except (ValueError, IndexError) as e:
            continue
        process.stdout.write(f'Connecting {host.name} ...\n')
        process.channel.set_echo(False)
        process.channel.set_line_mode(False)
        try:
            async with connect(host) as conn:
                term_type = process.get_terminal_type()
                term_size = process.get_terminal_size()
                chan, bash = await conn.create_session(
                        asyncssh.SSHClientProcess,
                        term_type=term_type,
                        term_size=term_size
                )
                bufsize = process.channel.get_write_buffer_size()
                await bash.redirect(
                        process.stdin,
                        process.stdout,
                        process.stderr,
                        bufsize=bufsize,
                        send_eof=False
                )
                await process.stdout.drain()
        except Exception as e:
            print(e)
            process.stdout.write('can not open connection\n')
    process.exit(0)


async def connect(host):
    if host.proxy is None:
        return await asyncssh.connect(
                host.hostname,
                username=host.username,
                client_keys=[expanduser(
                    config['client_key'].format(host.sshkey)
                )],
                known_hosts=None)
    tunnel = await connect(host_dict[host.proxy])
    return await tunnel.connect_ssh(
            host.hostname,
            username=host.username,
            client_keys=[expanduser(
                config['client_key'].format(host.sshkey)
            )],
            known_hosts=None)


class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        self.peername = conn.get_extra_info('peername')[0]
        print(f'SSH connection received from {self.peername}.')

    def connection_lost(self, exc):
        if exc:
            print(f'SSH connection error from {self.peername}: {exc}',
                  file=sys.stderr)
        else:
            print(f'SSH connection closed by {self.peername}.')

    def begin_auth(self, username):
        # If the user's password is the empty string, no auth is required
        return config['passwords'].get(username) != ''

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        pw = config['passwords'].get(username, '*')
        return crypt.crypt(password, pw) == pw


async def start_server():
    print(f"Starting ssh gateway server on "
          f"{config['listen']}:{config['port']} ...")
    await asyncssh.create_server(
            MySSHServer, config['listen'], config['port'],
            server_host_keys=list(map(expanduser, config['server_host_keys'])),
            authorized_client_keys=expanduser(
                config['authorized_client_keys']),
            process_factory=handle_client,
    )


def main():
    parser = argparse.ArgumentParser(description='SSH bastion server')
    parser.add_argument('-c', '--config', default='~/.sshgateway/config.toml')
    parser.add_argument('--show-config', dest='show', action='store_true',
                        default=False)
    args = parser.parse_args()
    try:
        with open(expanduser(args.config)) as configfile:
            config.update(pytoml.loads(configfile.read()))
    except FileNotFoundError:
        print('Can not find configuration file. use default config')
    except PermissionError:
        print('Can not read configuration file.', file=sys.stderr)
        sys.exit(1)
    except pytoml.TomlError as e:
        print(f'Invalid configuration file: {e}', file=sys.stderr)

    if args.show:
        print(pytoml.dumps(config))
        sys.exit(0)

    for host in config['hosts']:
        host.setdefault('proxy', None)

    try:
        config['hosts'] = [
                Host(**host) for host in config['hosts']]
        for host in config['hosts']:
            host_dict[host.name] = host

        config['groups'] = [
                Group(**group) for group in config['groups']]
        config['permissions'] = [
                Permission(**perm) for perm in config['permissions']]
    except Exception as e:
        print(f'Invalid configuration file: {e}')
        sys.exit(1)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_server())
    except (OSError, asyncssh.Error) as exc:
        sys.exit('Error starting server: ' + str(exc))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == '__main__':
    main()
