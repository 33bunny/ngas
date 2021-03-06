#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2012
#    Copyright by UWA (in the framework of the ICRAR)
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#
#******************************************************************************
#
# "@(#) $Id: ngamsDiscardCmd.py,v 1.4 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  04/04/2002  Created
#
"""
Contains code for handling the DISCARD command.

The DISCARD Command is used to remove file from the system. Two cases can be
handled:


1. Remove information about the file from the DB + remove the file
from the disk (if found).

Parameters: Disk ID, File ID and File Version.


2. Remove the file from the disk.

Parameter: Path.


When executing the DISCARD Command, the number of available copies of the
file in the archive it is not taken into account.
"""
# Man-page for the command.

import os

from ngamsLib.ngamsCore import getHostName, genLog, rmFile, TRACE, \
    NGAMS_DISCARD_CMD, NGAMS_HTTP_SUCCESS, NGAMS_SUCCESS, NGAMS_FAILURE
from ngamsLib import ngamsLib


_help = """
DISCARD - Command to discard (remove) files from the archive.

Parameters:
disk_id=(Disk ID)&file_id=(File ID)&file_version=(Version)

or

path=(Path)[&host_id=(Host ID)]
"""[1:-1]



def _delFile(srvObj,
             path,
             hostId,
             execute):
    """
    Delete (remove from disk) the file specified by the path on the given host.

    srvObj:        Reference to NG/AMS server class object (ngamsServer).

    path:          Path of file (string).

    hostId:        ID of host where file is stored (string).

    Returns:       Message with info about the execution (string).
    """
    if (hostId and (hostId != srvObj.getHostId())):
        raise Exception("DISCARD Command can only be executed locally!")

    # Handle the discard request locally.
    ngasHostId = "%s:%d" % (getHostName(), srvObj.getCfg().getPortNo())
    if (os.path.exists(path)):
        if (not ngamsLib.fileRemovable(path)):
            return genLog("NGAMS_ER_DISCARD_NOT_REM", [path, ngasHostId])
        if (not execute):
            msg = genLog("NGAMS_INFO_DISCARD_GRANTED", [path, ngasHostId])
        else:
            rmFile(path)
            if (os.path.exists(path)):
                return genLog("NGAMS_ER_DISCARD_FAILED",
                              [path, ngasHostId, "Not removable"])
            else:
                msg = genLog("NGAMS_INFO_DISCARD_OK", [path, ngasHostId])
    else:
        return genLog("NGAMS_ER_DISCARD_NOT_FOUND", [path, ngasHostId])

    return msg


def _discardFile(srvObj,
                 diskId = None,
                 fileId = None,
                 fileVersion = None,
                 hostId = None,
                 path = None,
                 execute = 0):
    """
    Discard a file from the system. If a Disk ID + File ID + File Version is
    given, the file must be stored on the contacted host in order to be
    executed.

    srvObj:        Reference to NG/AMS server class object (ngamsServer).

    diskId:        ID of disk hosting file or None (string|None).

    fileId:        ID of file or None (string|None).

    fileVersion:   File Version or None (integer|None).

    hostId:        ID of host where file is stored or None (string|None).

    path:          Path of file or None (string|None).

    execute:       If set to 1 the specified filel will be removed
                   (integer/0|1).

    tmpFilePat:    File pattern for temporary files (string).

    Returns:       Message indicating status of the execute (string).
    """
    T = TRACE()

    # Check the given paramereters.
    if (diskId and fileId and fileVersion):
        ngasHostId = "%s:%d" % (getHostName(), srvObj.getCfg().getPortNo())
        files = srvObj.getDb().getFileInfoFromFileId(fileId, fileVersion, diskId, ignore=None, dbCursor=False)
        if not files:
            err = genLog("NGAMS_ER_DISCARD_NOT_FOUND",
                         ["Disk ID: %s/File ID: %s/File Version: %s" %\
                          (str(diskId), str(fileId), str(fileVersion)),
                          ngasHostId])
            return err

        # Can only execute the DISCARD Command locally.
        fileInfo = files[0]
        hostId = fileInfo[-2]
        if (hostId != srvObj.getHostId()):
            raise Exception("DISCARD Command can only be executed locally!")

        mtPt = fileInfo[-1]
        filename = os.path.normpath(mtPt + "/" + fileInfo[1])
        _delFile(srvObj, filename, hostId, execute)
        if (execute):
            srvObj.getDb().deleteFileInfo(srvObj.getHostId(), diskId, fileId, fileVersion)
            msg = genLog("NGAMS_INFO_DISCARD_OK",
                         ["Disk ID: %s/File ID: %s/File Version: %s" %\
                          (str(diskId), str(fileId), str(fileVersion)),
                          ngasHostId])
        else:
            msg = genLog("NGAMS_INFO_DISCARD_GRANTED",
                         ["Disk ID: %s/File ID: %s/File Version: %s" %\
                          (str(diskId), str(fileId), str(fileVersion)),
                          ngasHostId])
    elif (path):
        msg = _delFile(srvObj, path, hostId, execute)
    else:
        msg = "Correct syntax is: disk_id=ID&file_id=ID&file_version=VER or "+\
              "path=PATH[&host_id=ID]"
        raise Exception(genLog("NGAMS_ER_CMD_SYNTAX",[NGAMS_DISCARD_CMD, msg]))

    return msg


def handleCmd(srvObj,
                     reqPropsObj,
                     httpRef):
    """
    Handle DISCARD Command.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        Void.
    """
    T = TRACE()

    if (reqPropsObj.hasHttpPar("help")):
        global _help
        return _help

    if (not srvObj.getCfg().getAllowRemoveReq()):
        errMsg = genLog("NGAMS_ER_ILL_REQ", ["Discard File"])
        raise Exception(errMsg)

    diskId      = None
    fileId      = None
    fileVersion = None
    hostId      = None
    path        = None
    execute     = 0
    if (reqPropsObj.hasHttpPar("disk_id")):
        diskId = reqPropsObj.getHttpPar("disk_id")
    if (reqPropsObj.hasHttpPar("file_id")):
        fileId = reqPropsObj.getHttpPar("file_id")
    if (reqPropsObj.hasHttpPar("file_version")):
        try:
            fileVersion = int(reqPropsObj.getHttpPar("file_version"))
        except ValueError:
            raise Exception("Illegal value for File Version specified: " +\
                  str(fileVersion))
    if (reqPropsObj.hasHttpPar("host_id")):
        hostId = reqPropsObj.getHttpPar("host_id")
    if (reqPropsObj.hasHttpPar("path")):
        path = reqPropsObj.getHttpPar("path")
    if (reqPropsObj.hasHttpPar("execute")):
        try:
            execute = int(reqPropsObj.getHttpPar("execute"))
        except:
            errMsg = genLog("NGAMS_ER_REQ_HANDLING", ["Must provide proper " +\
                            "value for parameter: execute (0|1)"])
            raise Exception(errMsg)

    msg = _discardFile(srvObj, diskId, fileId, fileVersion, hostId, path, execute)
    if msg.startswith("NGAMS_INFO_"):
        status = NGAMS_SUCCESS
    else:
        status = NGAMS_FAILURE

    httpRef.send_status(msg, status=status, code=NGAMS_HTTP_SUCCESS)