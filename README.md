# sshgateway
A ssh gateway server.

## Installation

`pip3 install sshgateway`

or

`pip3 install git+https://github.com/guyingbo/sshgateway.git`

if you do not have right to access system key file(), you can generate a keyfile on your own use command:

`ssh-keygen -t rsa -f ~/.sshgateway/ssh_host_rsa_key`

, then add

`server_host_keys = ['~/.sshgateway/ssh_host_rsa_key']`

to `~/.sshgateway/config.toml`.


generate configuration file:

~~~shell
mkdir ~/.sshgateway
sshgateway --show-config > ~/.sshgateway/config.toml
~~~

## Examples

### Configuration Example

~~~toml
banner = 'Welcome to bastion server, {username}!'
port = 8022

[passwords]
admin-1 = 'qV2iEadIGV2rw' # password of 'secretpw'
dev-user1 = '' # do not need password
test-user1 = ''

[[hosts]]
name = 'test-server'
hostname = 'xxx.xxx.xxx.xxx'
username = 'ubuntu'
sshkey = 'keyname'

[[hosts]]
name = 'dev-server'
hostname = 'xxx.xxx.xxx.xxx'
username = 'ubuntu'
sshkey = 'keyname'

[[groups]]
name = 'admin'
users = ['admin-1', 'admin-2']

[[groups]]
name = 'dev'
users = ['dev-user1', 'dev-user2']

[[groups]]
name = 'test'
users = ['test-user1', 'test-user2', 'test-user3']

[[permissions]]
groups = ['admin']
hostnames = ['.*']

[[permissions]]
groups = ['dev']
hostnames = ['^dev.*$']

[[permissions]]
groups = ['test']
hostnames = ['^test.*$']
~~~
