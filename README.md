# netsclaler-tool

## System Requirements
*  python >= 2.6 and python < 3
   * Have not yet tested with python 3
*  pip install -r requirements.txt

## NetScaler Requirements
*  Known to work with NS9.3
*  System user account that has appropriate access
  * Depending on your use case, you might only need a system user that is read-only

## Installation
1.  Copy netscalertool.conf.example to /etc/netscalertool.conf
1.  Update __user__ to a NetScaler system user
1.  Update __passwd__ for the NetScaler system user
1.  Optional
  * Update __manage_vservers__ with a list of vserver you want to manage
  * Update __external_nodes__ with a script that returns a newline separated list of
    hosts that are allowed to be managed
