#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: Uname_A.py,v 1.2 2003/10/01 23:40:51 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import re

from CommandParser import CommandParser

class Unix_df_k(CommandParser):
    
    command = 'df -k'

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    def condition(self, device, log):
        pp = device.getPrimaryPath()
        return "Linux" in pp or "Darwin" in pp

    def parse(self, device, results, log):
        log.info("collecting filesystems from device %s" % device.id)
        rm = self.newRelationshipMap("filesystems")
        rlines = results.split("\n")
        for line in rlines:
            aline = line.split()
            if len(aline) != 6: continue
            try:
                om = self.newObjectMap("ZenModel.FileSystem")
                om['storageDevice'] = aline[0]
                om['totalBytes'] = long(aline[1]) * 1024
                om['usedBytes'] = long(aline[2]) * 1024
                om['availBytes'] = long(aline[3]) * 1024
                cap = aline[4][-1] == "%" and aline[4][:-1] or aline[4]
                om['capacity'] = cap
                om['mount'] = aline[5]
                om['id'] = self.prepId.sub('-', om['mount'])
                rm.append(om)
            except ValueError: pass
        return rm

    def description(self):
        return "get df -k from server to build filesystems"
