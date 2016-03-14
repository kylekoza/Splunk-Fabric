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
@roles(['heavy_forwarders', 'master', 'search_heads', 'deployment_server', 'deployer'])
def deploy_splunk_pubkey():
    with cd("/tmp/"):
        run("wget {0}".format(splunk_signing_key))
        sudo("rpm --import SplunkPGPKey.pub")

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
