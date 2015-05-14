##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZentrapConfigs(Migrate.Step):
    "Add zentrap.filter.conf and alter zentrap.conf."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        ctx = sm.ServiceContext()

        zentrap = filter(lambda s: s.name == "zentrap", ctx.services)[0]

        # First update zentrap.conf.
        cf = filter(lambda f: f.name == "/opt/zenoss/etc/zentrap.conf", zentrap.configFiles)[0]
        cf.content = open(os.path.join(os.path.dirname(__file__), "config-files", "zentrap.5.1.0.conf"), 'r').read()

        # Now add zentrap.filter.conf.
        zentrap.configFiles.append( sm.ConfigFile (
            name = "/opt/zenoss/etc/zentrap.filter.conf",
            filename = "/opt/zenoss/etc/zentrap.filter.conf",
            owner = "zenoss:zenoss",
            permissions = "0664",
            content = open(os.path.join(os.path.dirname(__file__), "config-files", "zentrap.filter.5.1.0.conf"), 'r').read()
        ))

        # Commit our changes.
        ctx.commit()

UpdateZentrapConfigs()
