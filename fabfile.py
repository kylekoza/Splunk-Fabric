from __future__ import with_statement
from fabric.api import *
from fabric.operations import *
from fabric.context_managers import *
import getpass
import config

env.roledefs.update({
    'indexers': config.hosts['indexers'],
    'master': config.hosts['master'],
    'search_heads': config.hosts['search_heads'],
    'deployment_server': config.hosts['deployment_server'],
    'deployer': config.hosts['deployer'],
    'heavy_forwarders': config.hosts['heavy_forwarders'],
})

env.use_ssh_config = True
env.user = config.username
env.password = getpass.getpass('Please enter your remote sudo password: ')

passwords = {}

splunk_signing_key = "https://docs.splunk.com/images/6/6b/SplunkPGPKey.pub"

@task
@roles(['heavy_forwarders', 'indexers', 'search_heads'])
def deploy_splunk_pubkey():
    with cd("/tmp/"):
        run("wget {0}".format(splunk_signing_key))
        sudo("rpm --import SplunkPGPKey.pub")


@roles('master')
def set_maintenance(server):
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    with settings(sudo_user="splunk",
            prompts={"Do you want to continue? [y/n]: ": "y",
                     "Splunk username: ": "admin",
                     "Password: ": "{0}".format(current_pass)}):
        sudo("~/bin/splunk enable maintenance-mode")


@roles('master')
def unset_maintenance(server):
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    with settings(sudo_user="splunk",
            prompts={"Do you want to continue? [y/n]: ": "y",
                     "Splunk username: ": "admin",
                     "Password: ": "{0}".format(current_pass)}):
        sudo("~/bin/splunk disable maintenance-mode")


def upgrade_splunk():
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    sudo("yum -y upgrade")

    with settings(sudo_user="splunk",
             prompts={"Do you want to continue? [y/n]: ": "y",
                      "Splunk username: ": "admin",
                      "Password: ": "{0}".format(current_pass)}):
        sudo("~/bin/splunk stop")

    with cd('/tmp'):
        run('wget -O {0}'.format(config.splunk_url))
        run('rpm -K {0}'.format(config.splunk_url.split()[0]))
        sudo("yum -y localinstall {0}".format(config.splunk_url.split()[0]))

    with settings(sudo_user="splunk"):
        sudo("~/bin/splunk start --accept-license --answer-yes --no-prompt")


@roles('indexers')
def upgrade_indexers():
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    sudo("yum -y upgrade")

    with settings(sudo_user="splunk",
             prompts={"Do you want to continue? [y/n]: ": "y",
                      "Splunk username: ": "admin",
                      "Password: ": "{0}".format(current_pass)}):
        sudo("~/bin/splunk offline")

    with cd('/tmp'):
        run('wget -O {0}'.format(config.splunk_url))
        run('rpm -K {0}'.format(config.splunk_url.split()[0]))
        sudo("yum -y localinstall {0}".format(config.splunk_url.split()[0]))

    with settings(sudo_user="splunk"):
        sudo("~/bin/splunk start --accept-license --answer-yes --no-prompt")


@roles('search_heads', 'deployer')
@parallel(pool_size=3)
def upgrade_searchheads():
    execute(upgrade_splunk)


@roles('master', 'deployment_server')
@parallel
def upgrade_master():
    execute(upgrade_splunk)


@roles('heavy_forwarders')
@parallel(pool_size=2)
def upgrade_heavy_forwarders():
    execute(upgrade_splunk)


@roles('deployer', 'indexers', 'searchheads', 'deployment_server', 'master', 'heavy_forwarders')
def get_passwords():
    if not passwords.has_key(env.host):
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))


@task
def upgrade_index_cluster():
    execute(upgrade_master)
    set_maintenance(indexer_cluster_master)
    execute(upgrade_indexers)
    unset_maintenance(indexer_cluster_master)


@task
def upgrade_test_cluster():
    execute(upgrade_indexers)
    execute(upgrade_heavy_forwarders)
    execute(upgrade_searchheads)


@task
def upgrade_all():
    executre(get_passwords)
    execute(upgrade_index_cluster)
    execute(upgrade_searchheads)
    execute(upgrade_heavy_forwarders)


@task
@roles('deployer')
def deploy_searchapps():
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    remote_dir = "/opt/splunk/etc/shcluster/apps"
    with settings(sudo_user="splunk",
            prompts={'Do you wish to continue? [y/n]: ': 'y',
                     'Splunk username: ': 'admin',
                     'Password: ': current_pass}):
        sudo("ln -s ~/etc/shcluster/apps.git ~/etc/shcluster/apps/.git")
        with cd(remote_dir):
            sudo("git pull")
            sudo("rm .git")
        sudo("~/bin/splunk apply shcluster-bundle -target https://spl-search05.is.gatech.edu:8089")


@task
@roles('master')
def deploy_master():
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    remote_dir = "/opt/splunk/etc/master-apps/"
    with settings(sudo_user="splunk",
            prompts={'Splunk username: ': 'admin',
                     'Password: ': current_pass}):
        with cd(remote_dir):
            sudo("git pull")


@task
@roles('deployment_server')
def deploy_apps():
    if passwords.has_key(env.host):
        current_pass = passwords[env.host]
    else:
        passwords[env.host] = getpass.getpass("Password for splunk@{0}: ".format(env.host))
        current_pass = passwords[env.host]

    remote_dir = "/opt/splunk/etc/deployment-apps/"
    with settings(sudo_user="splunk",
            prompts={'Splunk username: ': 'admin',
                     'Password: ': current_pass}):
        with cd(remote_dir):
            sudo("git pull")
        sudo("~/bin/splunk reload deploy-server")


@task
@roles('indexers')
def test():
    print env.host
