from __future__ import with_statement
from fabric.api import *
from fabric.operations import *
from fabric.context_managers import *
import getpass

env.roledefs.update({
    'indexers': ['spl-index01.is.gatech.edu',
                 'spl-index02.is.gatech.edu',
                 'spl-index03.is.gatech.edu'],
    'master': ['spl-master.is.gatech.edu'],
    'search_heads': ['spl-search01.is.gatech.edu',
                     'spl-search02.is.gatech.edu',
                     'spl-search03.is.gatech.edu',
                     'spl-search04.is.gatech.edu',
                     'spl-search05.is.gatech.edu',
                     'spl-search06.is.gatech.edu',
                     'spl-search07.is.gatech.edu',],
    'deployment_server': ['spl-dep01.is.gatech.edu'],
    'deployer': ['spl-searchmaster.is.gatech.edu'],
    'heavy_forwarders': ['spl-hfwd01.is.gatech.edu',
                         'spl-hfwd02.is.gatech.edu',
                         'spl-hfwd03.is.gatech.edu',
                         'spl-hfwd04.is.gatech.edu',
                         'spl-hfwd05.is.gatech.edu',],
})

env.use_ssh_config = True

@task
@roles('deployer')
def deploy_searchapps():
    remote_dir = "/opt/splunk/etc/shcluster/apps"
    with settings(sudo_user="splunk", 
            prompts={'Do you wish to continue? [y/n]: ': 'y',
                     'Splunk username: ': 'admin'}):
        sudo("ln -s ~/etc/shcluster/apps.git ~/etc/shcluster/apps/.git")
        with cd(remote_dir):
            sudo("git pull")
            sudo("rm .git")
        sudo("~/bin/splunk apply shcluster-bundle -target https://spl-search05.is.gatech.edu:8089")


@task
@roles('master')
def deploy_master():
    remote_dir = "/opt/splunk/etc/master-apps/"
    with settings(sudo_user="splunk"):
        with cd(remote_dir):
            sudo("git pull")


@task
@roles('deployment_server')
def deploy_apps():
    remote_dir = "/opt/splunk/etc/deployment-apps/"
    with settings(sudo_user="splunk",
            prompts={'Splunk username: ': 'admin'}):
        with cd(remote_dir):
            sudo("git pull")
        sudo("~/bin/splunk reload deploy-server")
