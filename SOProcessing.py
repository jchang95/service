#! /usr/bin/env python

# SO files process
#    Process test file
#    Read expected result from its CFG file and compare to the actual result of the STA,ERR,PERR,AUTOCOR files.
#    If these two results are the same then the test PASS otherwise FAIL
#
# Usage: SOProcessing.exe
#

import sys
import os
import os.path
import ConfigParser                         #for parsing the config file
import time                                 #for current date and time
import wx,  wx.html                         #for wxpython, wx html header for about box
import SO_utils                             #SO_utils.py - common modules used with SO_process.py and create_new_cfg.py
import wx.lib.dialogs                       #for wx.lib.dialogs.ScrolledMessageDialog
import wx.lib.scrolledpanel                 #for scrolled panel
import wx.lib.agw.pybusyinfo as PBI         #for busy dialog
import subprocess                           #for subprocess Popen
import re                                   #for regular expression
import wx.lib.mixins.listctrl  as  listmix  #for editing on ListCtrl
from wx.lib.wordwrap import wordwrap        #wordwrap for Aboutbox

from threading import Timer                               #for watchdog with timer timeout
from watchdog.observers import Observer                   #for watchdog
from watchdog.events import PatternMatchingEventHandler   #for watchdog PatternMatchingEventHandler
from ObjectListView import ObjectListView, ColumnDefn     #for ObjectListView     - Cannot py2exe if using ObjectListView

# global variables
ALI_REC_LEN = 512
MSAG_REC_LEN = 200
MAX_PROGRESS = 20000

_msgAbout ="""
      Service Orders Processing:

     'Create new ALI / MSAG CFG'   creates new configuration file
      which contains the required parameters for a new test case.

     'Process ALI SO / MSAG SO'   runs CFG files, and obtains the results
     from various system generated data files which have its extension 
     as STA, ERR, AUTOCOR, PERR, MSTA, MERR. These results then would
     be compared to the required parameters of the configuration file
     to determine the test case PASS or FAIL.
     """


#overview = """<html><body>
#<h2><center>wx.AboutBox</center></h2>

#This function shows the native standard about dialog containing the
#information specified in info. If the current platform has a native
#about dialog which is capable of showing all the fields in info, the
#native dialog is used, otherwise the function falls back to the
#generic wxWidgets version of the dialog.

#</body></html>
#"""


aboutText = """
     <p><b>Service Orders Processing:</b></p>

     <p><b>Create new ALI / MSAG cfg</b></p>
     <p>Create new configuration file
      which contains the required parameters for a new test case.</p>

     <p><b>Process ALI / MSAG SO:</b></p>
     <p>Run CFG files, and obtain the
     results from various system generated data files which have 
     extensions as STA, ERR, AUTOCOR, PERR, MSTA, MERR, QERR.</p>
     <p>These results then would be compared to the required parameters
     of the configuration file to determine the test case PASS or FAIL.</p>
     
""" 

#for HTML OnAbout
#aboutText = """
#See <a href="http://www.telecomsys.com"> TeleCommunication System, Inc.</a></p>
#""" 

class HtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, id, size=(600,400)):
        wx.html.HtmlWindow.__init__(self,parent, id, size=size)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, link):
        wx.LaunchDefaultBrowser(link.GetHref())


class AboutBox(wx.Dialog):
    """
    USAGE:
        def OnAbout(self, event):
            dlg = AboutBox()
            dlg.ShowModal()
            dlg.Destroy()  
    """
    def __init__(self):
        wx.Dialog.__init__(self, None, -1, "About Service Orders Processing",
            style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.RESIZE_BORDER|
                wx.TAB_TRAVERSAL)
        hwin = HtmlWindow(self, -1, size=(400,200))
        hwin.SetPage(aboutText)

        btn = hwin.FindWindowById(wx.ID_OK)
        irep = hwin.GetInternalRepresentation()
        hwin.SetSize((irep.GetWidth()+25, irep.GetHeight()+10))
        self.SetClientSize(hwin.GetSize())
        self.CentreOnParent(wx.BOTH)
        self.SetFocus()


class MyPatternMatchingHandler(PatternMatchingEventHandler):
    patterns=["*.sta", "*.msta", "*.err", "*.merr", "*.err_*","*.sta_*", "*.msta_*", "*.mr_*", "*.qerr", "*.autocor", "*.perr"]    

    def process(self, event):
        """
        event.event_type
            'modified' | 'created' | 'moved' | 'deleted'
        event.is_directory
            True | False
        event.src_path
            path/to/observed/file
        """
        # a file with pattern matching is created on watch path - current working path
        print event
        
        # stop watchdog after the event occurred        
        global check
        global timeout
        
        check = 1        
        timeout = 0

    def on_modified(self, event):
        self.process(event)

    def on_created(self, event):
        self.process(event)


##class Watchdog():
##    def __init__(self, timeout, userHandler=None):  # timeout in seconds
##        self.timeout = timeout
##        self.handler = userHandler if userHandler is not None else self.defaultHandler
##        self.timer = Timer(self.timeout, self.handler)
##
##    def reset(self):
##        self.timer.cancel()
##        self.timer = Timer(self.timeout, self.handler)
##
##    def stop(self):
##        self.timer.cancel()
##
##    def defaultHandler(self):
##        raise self


#####################################################
class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    ''' TextEditMixin allows any column to be edited. '''
    
    #----------------------------------------------------------------------
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        """Constructor"""
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)



######################################################################
def SetMaxLength(instr, max):
    """
    Set max length for fields editing with ListCtrl
    """
    return instr.ljust(max,' ')[:max]


######################################################################
def SetMaxLength_OLD(instr, max):
    """
    Set max length for fields editing with ListCtrl
    """
    if (len(instr) > max):
        result = instr[0:max]
    elif (len(instr) < max):
        result = instr.ljust(max)
    elif (len(instr) == max):
        result = instr
    elif (len(instr) == 0):
        result = instr.ljust(max)
    return result
#######################################################################

def eraseElement(d,k):
    """
    Usage:
    exp = {'A':34, 'B':55, 'C':87}
    eraseElement(exp, 'B')

    Output:
    {'A': 34, 'C': 87}
    """
    if isinstance(d, dict):
        if k in d.keys():
            d.pop(k)
            print(d)
        else:
            print("Cannot find matching key")
    else:
        print("Not able to delete")


########################################################################
def process_data_chunk(line, dline, recno):
    """
    process one data chunk piece
    """ 
    if ((line[0:3] != 'UHL' and line[0:3] != 'UTL')):      # not adding header and trailer record
        print "line = [%s]\n" % line
        
        dline.update({str(recno):line})

        print "Record  %s" % recno    
        print len(line)

        recno += 1

    return dline, recno


#####################################################
def ALI_read_in_chunks(file_object, chunk_size=(ALI_REC_LEN + 1)):
    """
    Best method is to use iter & yield.

    'yield' is the keyword in python used for generator expressions.
    That means that the next time the function is called (or iterated on),
    the execution will start back up at the exact point it left off
    last time you called it.
    """
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


####################################################
def Read_from_ALI_file_OLV():
    prefixed = ''
    extension_list = ['dat', 'DAT']
    selected_ALI_datfilename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
    selectedpath, selectedfile = selected_ALI_datfilename

    currpath = selectedpath + "\\" + selectedfile
           
    if (os.path.exists(currpath)):
        dline = {}
        reccount = 0

        start = time.time()                               # start the stopwatch
        print "start timing:  %f" % start
        time.clock()

        # max = number higher than estimated number of records loading from file
        #max = MAX_PROGRESS        
        count = 0
        keepGoing = True       
        pdlg = wx.ProgressDialog("Loading data",
                           "Loading data from file",
                           maximum = MAX_PROGRESS,
                           parent=None,
                           style = wx.PD_CAN_ABORT |
                             wx.PD_APP_MODAL |
                              wx.PD_ELAPSED_TIME
                            | wx.PD_AUTO_HIDE
                            | wx.PD_REMAINING_TIME
                            )

        dfile = open(currpath, 'r')
        for line in ALI_read_in_chunks(dfile):
            retvar = process_data_chunk(line, dline, reccount)
            dline, reccount = retvar

            try:
                # start progress dialog
                while keepGoing and count <= reccount:
                    count += 1
                    wx.MilliSleep(1)
                    (keepGoing, skip) = pdlg.Update(count)
            except:
                #print "Exception in progress dialog"
                pdlg.Destroy()

        # close progress dialog
        keepGoing = False
        pdlg.Destroy()

        elapsedtime = time.time() - start                  # end timing
        print "end timing:  %f" % elapsedtime
            
        dfile.close()

    #print "reccount = %s\n" % reccount

    rcnt = 1
    #finally have data line dictionary
    for key in sorted(dline):
        if dline.has_key(str(key)):            
            line = dline[str(key)]            
            rcnt += 1
        else:
            print 'NONE'

    return line, dline, reccount, selectedpath, selectedfile, currpath, elapsedtime


#######################################################################
def set_ALI_columns(self, data=None):
        self.dataOlv.SetColumns([
            
        ColumnDefn("Function Code (Col: 1, max = 1)", "left", 60, "FOC"),
        ColumnDefn("NPA  (Col: 2 - 4, max = 3)", "left", 80, "NPA"),
        ColumnDefn("Calling Number  (Col: 5 - 11, max = 7)", "left", 120, "TN"),
        ColumnDefn("House Number (Col: 12 - 21, max = 10)", "left", 80, "HNum"),
        ColumnDefn("House Number Suffix  (Col: 22 - 25, max = 4)", "left", 40, "HNumSuffix"),
        ColumnDefn("Prefix Directional (Col: 26 - 27, max = 2)", "left", 40, "PrDir"),
        ColumnDefn("Street Name  (Col: 28 - 87, max = 60)", "left", 250, "streetname"),
        ColumnDefn("Street Suffix  (Col: 88 - 91, max = 4)", "left", 40, "SSfx"),
        ColumnDefn("Post Directional (Col: 92 - 93, max = 2)", "left", 40, "PoDir"),
        ColumnDefn("Community  (Col: 94 - 125, max = 32)", "left", 250, "community"),
        ColumnDefn("State  (Col: 126 - 127, max = 2)", "left", 40, "ST"),
        ColumnDefn("Location  (Col: 128 - 187, max = 60)", "left", 180, "location"),
        ColumnDefn("Customer Name  (Col: 188 - 219, max = 32)", "left", 180, "customername"),
        ColumnDefn("Class of Service (Col: 220, max = 1)", "left", 40, "CLS"),
        ColumnDefn("Type of Service  (Col: 221, max = 1)", "left", 40, "TOS"),
        ColumnDefn("Exchange (Col: 222 - 225, max = 4)", "left", 40, "XCH"),
        ColumnDefn("ESN  (Col: 226 - 230, max = 5)", "left", 60, "ESN"),
        ColumnDefn("Main NPA  (Col: 231 - 233, max = 3)", "left", 60, "MNPA"),
        ColumnDefn("Main Number  (Col: 234 - 240, max = 7)", "left", 100, "Main"),
        ColumnDefn("Order No  (Col: 241 - 250, max = 10)", "left", 80, "OrderNo"),
        ColumnDefn("Extract Date  (Col: 251 - 260, max = 6)", "left", 80, "ExDate"),
        ColumnDefn("County ID  (Col: 257 - 260, max = 4)", "left", 70, "COID"),
        ColumnDefn("Company ID-1  (Col: 261 - 265, max = 5)", "left", 70, "CID1"),
        ColumnDefn("Source ID  (Col: 266, max = 1)", "left", 40, "SID"),
        ColumnDefn("ZIP  (Col: 267 - 271, max = 5)", "left", 50, "ZIP"),
        ColumnDefn("ZIP4  (Col: 272 - 275, max = 4)", "left", 40, "ZIP4"),
        ColumnDefn("General Use  (Col: 276 - 286, max = 11)", "left", 250, "general"),
        ColumnDefn("Customer Code  (Col = 287 - 289, max = 3)", "left", 60, "CCD"),
        ColumnDefn("Comments  (Col: 290 - 319, max = 30)", "left", 120, "comments"),
        ColumnDefn("X Coordinate  (Col: 320 - 328, max = 9)", "left", 120, "XLON"),
        ColumnDefn("Y Coordinate  (Col: 329 - 337, max = 9)", "left", 120, "YLAT"),
        ColumnDefn("Z Coordinate  (Col: 338 - 342, max = 5)", "left", 100, "Zcoord"),
        ColumnDefn("Cell ID  (Col: 343 - 348, max = 6)", "left", 80, "CellID"),
        ColumnDefn("Sector ID  (Col: 349, max = 1)", "left", 40, "SecID"),
        ColumnDefn("TAR Code  (Col: 350 - 355, max = 6)", "left", 40, "TAR"),
        ColumnDefn("Reserved1  (Col: 356 - 376, max = 21)", "left", 200, "reserved1"),
        ColumnDefn("ALT  (Col: 377 - 386, max = 10)", "left", 90, "ALT"),
        ColumnDefn("Expanded Extract Date  (Col: 387 - 394, max = 8)", "left", 100, "EEDate"),
        ColumnDefn("NENAreserved  (Col: 395 - 475, max = 81)", "left", 220, "NENAreserved"),
        ColumnDefn("Company ID-2  (Col: 476 - 480, max = 5)", "left", 70, "CID2"),
        ColumnDefn("Reserved2  (Col: 481 - 511, max = 31)", "left", 120, "reserved2"),
        ColumnDefn("EOR  (Col: 512, max = 1)", "left", 40, "EOR")
            
        ])

        self.dataOlv.CreateCheckStateColumn()

        #self.olv1.SetColumnFixedWidth(0, 16)    # the first column is fixed to 16 pixel wide
        #self.titleColumn.minimumWidth = 30      # will stop the "Title" column from becoming less than 30 pixels in width
        #self.titleColumn.maximumWidth = 120     # will set the "Title" column from becoming more than 120 pixels in width
        #self.statusColumn = ColumnDefn("", imageGetter=statusImageGetter, fixedWidth=16)     # make a column be fixed width and unresizable by the user

######################################################################
def GetText_from_ALI_columns_currRow_OLV_3(self, row):

        lineout = []

        # ignore the check status column 0
        
        item = self.dataOlv.GetItemText(row, 1)
        FOC = SetMaxLength(item, 1)
        print "FOC = [%s]   length = %d\n" % (FOC, len(FOC))
        

        item = self.dataOlv.GetItemText(row, 2)
        NPA = SetMaxLength(item, 3)
        print "NPA = [%s]   length = %d\n" % (NPA, len(NPA))
        
        item = self.dataOlv.GetItemText(row, 3)
        TN = SetMaxLength(item, 7)
        print "TN = [%s]   length = %d\n" % (TN, len(TN))

        
        item = self.dataOlv.GetItemText(row, 4)
        HNum = SetMaxLength(item, 10)
        print "HNum = [%s]  -  length = %s\n" % (HNum, len(HNum))
        
        item = self.dataOlv.GetItemText(row, 5)
        HNumSuffix = SetMaxLength(item, 4)
        print "HNumSuffix = [%s]   length = %d\n" % (HNumSuffix, len(HNumSuffix))

        
        item = self.dataOlv.GetItemText(row, 6)
        PrDir = SetMaxLength(item, 2)
        print "PrDir = [%s]   length = %d\n" % (PrDir, len(PrDir))

        item = self.dataOlv.GetItemText(row, 7)
        streetname = SetMaxLength(item, 60)
        print "streetname = [%s]  -  length = %s\n" % (streetname, len(streetname))
        
        item = self.dataOlv.GetItemText(row, 8)
        SSfx = SetMaxLength(item, 4)
        print "SSfx = [%s]   length = %d\n" % (SSfx, len(SSfx))

        
        item = self.dataOlv.GetItemText(row, 9)
        PoDir = SetMaxLength(item, 2)
        print "PoDir = [%s]   length = %d\n" % (PoDir, len(PoDir))


        item = self.dataOlv.GetItemText(row, 10)
        community = SetMaxLength(item, 32)
        print "community = [%s]   length = %d\n" % (community, len(community))
        
        item = self.dataOlv.GetItemText(row, 11)
        ST =  SetMaxLength(item, 2)
        print "ST = [%s]   length = %d\n" % (ST, len(ST))
        
        item = self.dataOlv.GetItemText(row, 12)
        location = SetMaxLength(item, 60)
        print "location = [%s]   length = %d\n" % (location, len(location))
        
        item = self.dataOlv.GetItemText(row, 13)
        customername = SetMaxLength(item, 32)
        print "customername = [%s]   length = %d\n" % (customername, len(customername))
        
        item = self.dataOlv.GetItemText(row, 14)
        CLS = SetMaxLength(item, 1)
        print "CLS = [%s]   length = %d\n" % (CLS, len(CLS))
        
        item = self.dataOlv.GetItemText(row, 15)
        TOS = SetMaxLength(item, 1)
        print "TOS = [%s]   length = %d\n" % (TOS, len(TOS))
        
        item = self.dataOlv.GetItemText(row, 16)
        XCH = SetMaxLength(item, 4)
        print "XCH = [%s]   length = %d\n" % (XCH, len(XCH))
        
        item = self.dataOlv.GetItemText(row, 17)
        ESN = SetMaxLength(item, 5)
        print "ESN = [%s]   length = %d\n" % (ESN, len(ESN))
        
        item = self.dataOlv.GetItemText(row, 18)
        MNPA = SetMaxLength(item, 3)
        print "MNPA = [%s]   length = %d\n" % (MNPA, len(MNPA))
        
        item = self.dataOlv.GetItemText(row, 19)
        Main = SetMaxLength(item, 7)
        print "Main = [%s]   length = %d\n" % (Main, len(Main))
        
        item = self.dataOlv.GetItemText(row, 20)
        OrderNo = SetMaxLength(item, 10)
        print "OrderNo = [%s]   length = %d\n" % (OrderNo, len(OrderNo))
        
        item = self.dataOlv.GetItemText(row, 21)
        ExDate = SetMaxLength(item, 6)
        print "ExDate = [%s]   length = %d\n" % (ExDate, len(ExDate))
        
        item = self.dataOlv.GetItemText(row, 22)
        COID = SetMaxLength(item, 4)
        print "COID = [%s]   length = %d\n" % (COID, len(COID))
        
        item = self.dataOlv.GetItemText(row, 23)
        CID1 = SetMaxLength(item, 5)
        print "CID1 = [%s]   length = %d\n" % (CID1, len(CID1))
        
        item = self.dataOlv.GetItemText(row, 24)
        SID = SetMaxLength(item, 1)
        print "SID = [%s]   length = %d\n" % (SID, len(SID))
        
        item = self.dataOlv.GetItemText(row, 25)
        ZIP = SetMaxLength(item, 5)
        print "ZIP = [%s]   length = %d\n" % (ZIP, len(ZIP))
        
        item = self.dataOlv.GetItemText(row, 26)
        ZIP4 = SetMaxLength(item, 4)
        print "ZIP4= [%s]   length = %d\n" % (ZIP4, len(ZIP4))
        
        item = self.dataOlv.GetItemText(row, 27)
        general = SetMaxLength(item, 11)
        print "general = [%s]   length = %d\n" % (general, len(general))
        
        item = self.dataOlv.GetItemText(row, 28)
        CCD = SetMaxLength(item, 3)
        print "CCD = [%s]   length = %d\n" % (CCD, len(CCD))
        
        item = self.dataOlv.GetItemText(row, 29)
        comments = SetMaxLength(item, 30)
        print "comments = [%s]   length = %d\n" % (comments, len(comments))
        
        item = self.dataOlv.GetItemText(row, 30)
        XLON = SetMaxLength(item, 9)
        print "XLON = [%s]   length = %d\n" % (XLON, len(XLON))
        
        item = self.dataOlv.GetItemText(row, 31)
        YLAT = SetMaxLength(item, 9)
        print "YLAT = [%s]   length = %d\n" % (YLAT, len(YLAT))
        
        item = self.dataOlv.GetItemText(row, 32)
        Zcoord = SetMaxLength(item, 5)
        print "Zcoord = [%s]   length = %d\n" % (Zcoord, len(Zcoord))
        
        item = self.dataOlv.GetItemText(row, 33)
        CellID = SetMaxLength(item, 6)
        print "CellID = [%s]   length = %d\n" % (CellID, len(CellID))
        
        item = self.dataOlv.GetItemText(row, 34)
        SecID = SetMaxLength(item, 1)
        print "SecID = [%s]   length = %d\n" % (SecID, len(SecID))
        
        item = self.dataOlv.GetItemText(row, 35)
        TAR = SetMaxLength(item, 6)
        print "TAR = [%s]   length = %d\n" % (TAR, len(TAR))
        
        item = self.dataOlv.GetItemText(row, 36)
        reserved1 = SetMaxLength(item, 21)
        print "reserved1 = [%s]   length = %d\n" % (reserved1, len(reserved1))
        
        item = self.dataOlv.GetItemText(row, 37)
        ALT = SetMaxLength(item, 10)
        print "ALT = [%s]   length = %d\n" % (ALT, len(ALT))
        
        item = self.dataOlv.GetItemText(row, 38)
        EEDate = SetMaxLength(item, 8)
        print "EEDate = [%s]   length = %d\n" % (EEDate, len(EEDate))
        
        item = self.dataOlv.GetItemText(row, 39)
        NENAreserved = SetMaxLength(item, 81)
        print "NENAreserved = [%s]   length = %d\n" % (NENAreserved, len(NENAreserved))
        
        item = self.dataOlv.GetItemText(row, 40)
        CID2 = SetMaxLength(item, 5)
        print "CID2 = [%s]   length = %d\n" % (CID2, len(CID2))
        
        item = self.dataOlv.GetItemText(row, 41)
        reserved2 = SetMaxLength(item, 31)
        print "reserved2 = [%s]   length = %d\n" % (reserved2, len(reserved2))
        
        item = self.dataOlv.GetItemText(row, 42)
        EOR = SetMaxLength(item, 1)
        print "EOR = [%s]   length = %d\n" % (EOR, len(EOR))

        lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
            PoDir + community + ST + location + customername + CLS + TOS +   \
            XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
            SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
            Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
            NENAreserved + CID2 + reserved2 + EOR

        
        #print len(lineout)
        #print lineout
        
        return lineout


####################################################
def Read_from_ALI_file():
    prefixed = ''
    extension_list = ['dat', 'DAT']
    selected_ALI_datfilename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
    selectedpath, selectedfile = selected_ALI_datfilename

    currpath = selectedpath + "\\" + selectedfile
           
    if (os.path.exists(currpath)):
        dline = {}
        reccount = 0

        start = time.time()                               # start the stopwatch
        print "start timing:  %f" % start
        time.clock()

        # max = number higher than estimated number of records loading from file
        #max = MAX_PROGRESS        
        count = 0
        keepGoing = True       
        pdlg = wx.ProgressDialog("Loading data",
                           "Loading data from file",
                           maximum = MAX_PROGRESS,
                           parent=None,
                           style = wx.PD_CAN_ABORT |
                             wx.PD_APP_MODAL |
                              wx.PD_ELAPSED_TIME
                            | wx.PD_AUTO_HIDE
                            | wx.PD_REMAINING_TIME
                            )

        dfile = open(currpath, 'r')
        for line in ALI_read_in_chunks(dfile):
            retvar = process_data_chunk(line, dline, reccount)
            dline, reccount = retvar

            try:
                # start progress dialog
                while keepGoing and count < reccount:
                    count += 1
                    wx.MilliSleep(1)
                    (keepGoing, skip) = pdlg.Update(count)
            except:
                print "Exception in progress dialog"
                pdlg.Destroy()

        # close progress dialog
        keepGoing = False
        pdlg.Destroy()

        elapsedtime = time.time() - start                  # end timing
        print "end timing:  %f" % elapsedtime
            
        dfile.close()

    #print "reccount = %s\n" % reccount

    rcnt = 1
    #finally have data line dictionary
    for key in sorted(dline):
        if dline.has_key(str(key)):            
            line = dline[str(key)]            
            rcnt += 1
        else:
            print 'NONE'

    return dline, reccount, selectedpath, selectedfile, currpath,elapsedtime


########################################################################
def insert_ALI_column_to_list_ctrl(self):    
        # insert columns to self.list_ctrl
        self.list_ctrl.InsertColumn(0, "Function Code (Col: 1, max = 1)")
        self.list_ctrl.InsertColumn(1, "NPA  (Col: 2 - 4, max = 3)")
        self.list_ctrl.InsertColumn(2, "Calling Number  (Col: 5 - 11, max = 7)")
        self.list_ctrl.InsertColumn(3, "House Number (Col: 12 - 21, max = 10)")
        self.list_ctrl.InsertColumn(4, "House Number Suffix  (Col: 22 - 25, max = 4)")
        self.list_ctrl.InsertColumn(5, "Prefix Directional (Col: 26 - 27, max = 2)")
        self.list_ctrl.InsertColumn(6, "Street Name  (Col: 28 - 87, max = 60)")
        self.list_ctrl.InsertColumn(7, "Street Suffix  (Col: 88 - 91, max = 4)")
        self.list_ctrl.InsertColumn(8, "Post Directional (Col: 92 - 93, max = 2)")
        self.list_ctrl.InsertColumn(9, "Community  (Col: 94 - 125, max = 32)")
        self.list_ctrl.InsertColumn(10, "State  (Col: 126 - 127, max = 2)")
        self.list_ctrl.InsertColumn(11, "Location  (Col: 128 - 187, max = 60)")
        self.list_ctrl.InsertColumn(12, "Customer Name  (Col: 188 - 219, max = 32)")
        self.list_ctrl.InsertColumn(13, "Class of Service (Col: 220, max = 1)")
        self.list_ctrl.InsertColumn(14, "Type of Service  (Col: 221, max = 1)")
        self.list_ctrl.InsertColumn(15, "Exchange (Col: 222 - 225, max = 4)")
        self.list_ctrl.InsertColumn(16, "ESN  (Col: 226 - 230, max = 5)")
        self.list_ctrl.InsertColumn(17, "Main NPA  (Col: 231 - 233, max = 3)")
        self.list_ctrl.InsertColumn(18, "Main Number  (Col: 234 - 240, max = 7)")
        self.list_ctrl.InsertColumn(19, "Order No  (Col: 241 - 250, max = 10)")
        self.list_ctrl.InsertColumn(20, "Extract Date  (Col: 251 - 260, max = 6)")
        self.list_ctrl.InsertColumn(21, "County ID  (Col: 257 - 260, max = 4)")
        self.list_ctrl.InsertColumn(22, "Company ID-1  (Col: 261 - 265, max = 5)")
        self.list_ctrl.InsertColumn(23, "Source ID  (Col: 266, max = 1)")
        self.list_ctrl.InsertColumn(24, "ZIP  (Col: 267 - 271, max = 5)")
        self.list_ctrl.InsertColumn(25, "ZIP4  (Col: 272 - 275, max = 4)")
        self.list_ctrl.InsertColumn(26, "general  (Col: 276 - 286, max = 11)")
        self.list_ctrl.InsertColumn(27, "Customer Code  (Col = 287 - 289, max = 3)")
        self.list_ctrl.InsertColumn(28, "Comments  (Col: 290 - 319, max = 30)")
        self.list_ctrl.InsertColumn(29, "X Coordinate  (Col: 320 - 328, max = 9)")
        self.list_ctrl.InsertColumn(30, "Y Coordinate  (Col: 329 - 337, max = 9)")
        self.list_ctrl.InsertColumn(31, "Z Coordinate  (Col: 338 - 342, max = 5)")
        self.list_ctrl.InsertColumn(32, "Cell ID  (Col: 343 - 348, max = 6)")
        self.list_ctrl.InsertColumn(33, "Sector ID  (Col: 349, max = 1)")
        self.list_ctrl.InsertColumn(34, "TAR Code  (Col: 350 - 355, max = 6)")
        self.list_ctrl.InsertColumn(35, "Reserved1  (Col: 356 - 376, max = 21)")
        self.list_ctrl.InsertColumn(36, "ALT  (Col: 377 - 386, max = 10)")
        self.list_ctrl.InsertColumn(37, "Expanded Extract Date  (Col: 387 - 394, max = 8)")
        self.list_ctrl.InsertColumn(38, "NENAreserved  (Col: 395 - 475, max = 81)")
        self.list_ctrl.InsertColumn(39, "Company ID-2  (Col: 476 - 480, max = 5)")
        self.list_ctrl.InsertColumn(40, "reserved2  (Col: 481 - 511, max = 31)")
        self.list_ctrl.InsertColumn(41, "EOR  (Col: 512, max = 1)")    


##################################################################
def insert_string_ALI_items_to_list_ctrl(self, index, FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,                   \
                                                    community,ST,location,customername,CLS,TOS,XCH,ESN,MNPA,Main,OrderNo,          \
                                                    ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,   \
                                                    SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR):
    
        self.list_ctrl.InsertStringItem(index, FOC)
        self.list_ctrl.SetStringItem(index, 1, NPA)
        self.list_ctrl.SetStringItem(index, 2, TN)
        self.list_ctrl.SetStringItem(index, 3, HNum)
        self.list_ctrl.SetStringItem(index, 4, HNumSuffix)
        self.list_ctrl.SetStringItem(index, 5, PrDir)
        self.list_ctrl.SetStringItem(index, 6, streetname)
        self.list_ctrl.SetStringItem(index, 7, SSfx)
        self.list_ctrl.SetStringItem(index, 8, PoDir)
        self.list_ctrl.SetStringItem(index, 9, community)
        self.list_ctrl.SetStringItem(index, 10, ST)
        self.list_ctrl.SetStringItem(index, 11, location)
        self.list_ctrl.SetStringItem(index, 12, customername)
        self.list_ctrl.SetStringItem(index, 13, CLS)
        self.list_ctrl.SetStringItem(index, 14, TOS)
        self.list_ctrl.SetStringItem(index, 15, XCH)
        self.list_ctrl.SetStringItem(index, 16, ESN)
        self.list_ctrl.SetStringItem(index, 17, MNPA)
        self.list_ctrl.SetStringItem(index, 18, Main)
        self.list_ctrl.SetStringItem(index, 19, OrderNo)
        self.list_ctrl.SetStringItem(index, 20, ExDate)
        self.list_ctrl.SetStringItem(index, 21, COID)
        self.list_ctrl.SetStringItem(index, 22, CID1)
        self.list_ctrl.SetStringItem(index, 23, SID)
        self.list_ctrl.SetStringItem(index, 24, ZIP)
        self.list_ctrl.SetStringItem(index, 25, ZIP4)
        self.list_ctrl.SetStringItem(index, 26, general)
        self.list_ctrl.SetStringItem(index, 27, CCD)
        self.list_ctrl.SetStringItem(index, 28, comments)
        self.list_ctrl.SetStringItem(index, 29, XLON)
        self.list_ctrl.SetStringItem(index, 30, YLAT)
        self.list_ctrl.SetStringItem(index, 31, Zcoord)
        self.list_ctrl.SetStringItem(index, 32, CellID)
        self.list_ctrl.SetStringItem(index, 33, SecID)
        self.list_ctrl.SetStringItem(index, 34, TAR)
        self.list_ctrl.SetStringItem(index, 35, reserved1)
        self.list_ctrl.SetStringItem(index, 36, ALT)
        self.list_ctrl.SetStringItem(index, 37, EEDate)
        self.list_ctrl.SetStringItem(index, 38, NENAreserved)
        self.list_ctrl.SetStringItem(index, 39, CID2)
        self.list_ctrl.SetStringItem(index, 40, reserved2)
        self.list_ctrl.SetStringItem(index, 41, EOR)


########################################################################
def obtain_ALI_fields_from_line(line):
    """
    obtain ALI fields name from data line
    """
    line.strip('\n')

    FOC     = line[0]               #FOC           edit1   1     col  1
    NPA     = line[1:4]            #NPA           edit2  3      col  2-4
    TN       = line[4:11]          #TN             edit3  7      col  5-11
    HNum  = line[11:21]        #HNum        edit4  10    col 12-21
    HNumSuffix = line[21:25]     #HNumSuffix   edit5  4     col 22-25
    PrDir     = line[25:27]        #PrDir        edit6  2       col 26-27
    streetname = line[27:87]   #streetname   edit7  60        col 28-87
    SSfx      = line[87:91]        #SSfx         edit8  4        col 88-91
    PoDir    = line[91:93]        #PoDir        edit9  2        col 92-93
    community  = line[93:125]     #community    edit10 32     col 94-125
    ST         = line[125:127]         #ST           edit11 2             col 126-127
    location   = line[127:187]      #location     edit12 60         col 128-187
    customername = line[187:219]      #customername edit13 32    col 188-219
    CLS       = line[219]                       #CLS          edit14 1      col 220
    TOS       = line[220]                       #TOS          edit15 1      col 221
    XCH      = line[221:225]                #XCH          edit16 4      col 222-225
    ESN       = line[225:230]                #ESN          edit17 5      col 226-230
    MNPA    = line[230:233]                #MNPA         edit18 3    col 231-233
    Main      = line[233:240]                #Main         edit19 7      col  234-240
    OrderNo = line[240:250]               #OrderNo      edit20 10    col 241-250
    ExDate   = line[250:256]               #ExDate       edit21 6      col  251-256
    COID      = line[256:260]               #COID         edit22 4      col 257-260
    CID1      = line[260:265]               #CID1         edit23 5       col 261-265
    SID        = line[265]                       #SID          edit24 1        col 266
    ZIP         = line[266:271]               #ZIP          edit25 5         col 267-271
    ZIP4       = line[271:275]               #ZIP4         edit26 4        col 272-275
    general   = line[275:286]               #general      edit27 11     col 276-286
    CCD       = line[286:289]                #CCD          edit28 3      col 287-289
    comments  = line[289:319]           #comments     edit29 30   col 290-319
    XLON     = line[319:328]               #XLON         edit30 9       col 320-328
    YLAT      = line[328:337]                #YLAT         edit31 9       col 329-337
    Zcoord   = line[337:342]               #Zcoord       edit32 5      col 338-342
    CellID     = line[342:348]               #CellID       edit33 6       col  343-348
    SecID     = line[348]                      #SecID        edit34 1       col  349
    TAR       = line[349:355]                #TAR          edit35 6       col 350-355
    reserved1 = line[355:376]             #reserved1    edit36 21    col  356-376
    ALT        = line[376:386]                #ALT          edit37 10      col  377-386
    EEDate    = line[386:394]              #EEDate       edit38 8       col  387-394
    NENAreserved  = line[394:475]     #NENAreserved edit39 81    col  395-475
    CID2       = line[475:480]              #CID2         edit40 5     col 476-480
    reserved2   = line[480:511]           #reserved2    edit41 31     col 481-511
    EOR        = line[511]                     #EOR          edit42 1 (*)      col 512

    return  FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
            MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                \
            SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR


########################################################################
def default_ALI_fields_for_new_record():
    """
    set default values of ALI fields to new ALI record
    """

    FOC           = "I"                    #FOC           edit1   1     col  1
    NPA           = "123"                  #NPA           edit2  3      col  2-4
    TN            = "4567890"              #TN             edit3  7      col  5-11
    HNum          = "1234567890"           #HNum        edit4  10    col 12-21
    HNumSuffix    = "    "                 #HNumSuffix   edit5  4     col 22-25
    PrDir         = "  "                   #PrDir        edit6  2       col 26-27
    streetname    = "123456789-123456789-123456789-123456789-123456789-123456789-"            #streetname   edit7  60        col 28-87
    SSfx          = "    "                 #SSfx         edit8  4        col 88-91
    PoDir         = "  "                   #PoDir        edit9  2        col 92-93
    community     = "123456789-123456789-123456789-12"           #community    edit10 32     col 94-125
    ST            = "TN"                   #ST           edit11 2             col 126-127
    location      = "123456789-123456789-123456789-123456789-123456789-123456789-"      #location     edit12 60         col 128-187
    customername  = "123456789-123456789-123456789-12"      #customername edit13 32    col 188-219
    CLS           = "0"                       #CLS          edit14 1      col 220
    TOS           = "0"                       #TOS          edit15 1      col 221
    XCH           = "1234"                    #XCH          edit16 4      col 222-225
    ESN           = "12345"                   #ESN          edit17 5      col 226-230
    MNPA          = "123"                     #MNPA         edit18 3    col 231-233
    Main          = "1234567"                 #Main         edit19 7      col  234-240
    OrderNo       = "123456789-"              #OrderNo      edit20 10    col 241-250
    ExDate        = "MMDDYY"                  #ExDate       edit21 6      col  251-256
    COID          = "    "                    #COID         edit22 4      col 257-260
    CID1          = "ABCDE"                   #CID1         edit23 5       col 261-265
    SID           = " "                       #SID          edit24 1        col 266
    ZIP           = "     "                   #ZIP          edit25 5         col 267-271
    ZIP4          = "    "                    #ZIP4         edit26 4        col 272-275
    general       = "123456789-1"             #general      edit27 11     col 276-286
    CCD           = "123"                     #CCD          edit28 3      col 287-289
    comments      = "123456789-123456789-123456789-"        #comments     edit29 30   col 290-319
    XLON          = "123456789"               #XLON         edit30 9       col 320-328
    YLAT          = "123456789"               #YLAT         edit31 9       col 329-337
    Zcoord        = "12345"                   #Zcoord       edit32 5      col 338-342
    CellID        = "123456"                  #CellID       edit33 6       col  343-348
    SecID         = " "                       #SecID        edit34 1       col  349
    TAR           = "123456"                  #TAR          edit35 6       col 350-355
    reserved1     = "123456789-123456789-1"   #reserved1    edit36 21    col  356-376
    ALT           = "123456789-"              #ALT          edit37 10      col  377-386
    EEDate        = "YYYYMMDD"                #EEDate       edit38 8       col  387-394
    NENAreserved  = "123456789-123456789-123456789-123456789-123456789-123456789-123456789-123456789-1"     #NENAreserved edit39 81    col  395-475
    CID2          = "12345"                   #CID2         edit40 5     col 476-480
    reserved2     = "123456789-123456789-123456789-1"           #reserved2    edit41 31     col 481-511
    EOR           = "*"                       #EOR          edit42 1 (*)      col 512

    return  FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
            MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                \
            SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR


######################################################################
def GetText_from_ALI_columns_currRow(self, row):

    lineout = []
        
    item = self.list_ctrl.GetItem(itemId=row, col=0)
    FOC = SetMaxLength(item.GetText(), 1)
    #print "FOC = [%s]\n" % FOC

    item = self.list_ctrl.GetItem(itemId=row, col=1)
    NPA = SetMaxLength(item.GetText(), 3)
    #print "NPA = [%s]\n" % NPA
        
    item = self.list_ctrl.GetItem(itemId=row, col=2)
    TN = SetMaxLength(item.GetText(), 7)
    #print "TN = [%s]\n" % TN
        
    item = self.list_ctrl.GetItem(itemId=row, col=3)
    HNum = SetMaxLength(item.GetText(), 10)
    #print "HNum = [%s]  -  length = %s\n" % (HNum, len(HNum))
        
    item = self.list_ctrl.GetItem(itemId=row, col=4)
    HNumSuffix = SetMaxLength(item.GetText(), 4)
        
    item = self.list_ctrl.GetItem(itemId=row, col=5)
    PrDir = SetMaxLength(item.GetText(), 2)
        
    item = self.list_ctrl.GetItem(itemId=row, col=6)
    streetname = SetMaxLength(item.GetText(), 60)
    #print "streetname = [%s]  -  length = %s\n" % (streetname, len(streetname))
        
    item = self.list_ctrl.GetItem(itemId=row, col=7)
    SSfx = SetMaxLength(item.GetText(), 4)
        
    item = self.list_ctrl.GetItem(itemId=row, col=8)
    PoDir = SetMaxLength(item.GetText(), 2)
        
    item = self.list_ctrl.GetItem(itemId=row, col=9)
    community = SetMaxLength(item.GetText(), 32)
        
    item = self.list_ctrl.GetItem(itemId=row, col=10)
    ST =  SetMaxLength(item.GetText(), 2)
        
    item = self.list_ctrl.GetItem(itemId=row, col=11)
    location = SetMaxLength(item.GetText(), 60)
        
    item = self.list_ctrl.GetItem(itemId=row, col=12)
    customername = SetMaxLength(item.GetText(), 32)
        
    item = self.list_ctrl.GetItem(itemId=row, col=13)
    CLS = SetMaxLength(item.GetText(), 1)
        
    item = self.list_ctrl.GetItem(itemId=row, col=14)
    TOS = SetMaxLength(item.GetText(), 1)
        
    item = self.list_ctrl.GetItem(itemId=row, col=15)
    XCH = SetMaxLength(item.GetText(), 4)
        
    item = self.list_ctrl.GetItem(itemId=row, col=16)
    ESN = SetMaxLength(item.GetText(), 5)
        
    item = self.list_ctrl.GetItem(itemId=row, col=17)
    MNPA = SetMaxLength(item.GetText(), 3)
        
    item = self.list_ctrl.GetItem(itemId=row, col=18)
    Main = SetMaxLength(item.GetText(), 7)
        
    item = self.list_ctrl.GetItem(itemId=row, col=19)
    OrderNo = SetMaxLength(item.GetText(), 10)
        
    item = self.list_ctrl.GetItem(itemId=row, col=20)
    ExDate = SetMaxLength(item.GetText(), 6)
        
    item = self.list_ctrl.GetItem(itemId=row, col=21)
    COID = SetMaxLength(item.GetText(), 4)
        
    item = self.list_ctrl.GetItem(itemId=row, col=22)
    CID1 = SetMaxLength(item.GetText(), 5)
        
    item = self.list_ctrl.GetItem(itemId=row, col=23)
    SID = SetMaxLength(item.GetText(), 1)
        
    item = self.list_ctrl.GetItem(itemId=row, col=24)
    ZIP = SetMaxLength(item.GetText(), 5)
        
    item = self.list_ctrl.GetItem(itemId=row, col=25)
    ZIP4 = SetMaxLength(item.GetText(), 4)
        
    item = self.list_ctrl.GetItem(itemId=row, col=26)
    general = SetMaxLength(item.GetText(), 11)
        
    item = self.list_ctrl.GetItem(itemId=row, col=27)
    CCD = SetMaxLength(item.GetText(), 3)
        
    item = self.list_ctrl.GetItem(itemId=row, col=28)
    comments = SetMaxLength(item.GetText(), 30)
        
    item = self.list_ctrl.GetItem(itemId=row, col=29)
    XLON = SetMaxLength(item.GetText(), 9)
        
    item = self.list_ctrl.GetItem(itemId=row, col=30)
    YLAT = SetMaxLength(item.GetText(), 9)
        
    item = self.list_ctrl.GetItem(itemId=row, col=31)
    Zcoord = SetMaxLength(item.GetText(), 5)
        
    item = self.list_ctrl.GetItem(itemId=row, col=32)
    CellID = SetMaxLength(item.GetText(), 6)
        
    item = self.list_ctrl.GetItem(itemId=row, col=33)
    SecID = SetMaxLength(item.GetText(), 1)
        
    item = self.list_ctrl.GetItem(itemId=row, col=34)
    TAR = SetMaxLength(item.GetText(), 6)
        
    item = self.list_ctrl.GetItem(itemId=row, col=35)
    reserved1 = SetMaxLength(item.GetText(), 21)
        
    item = self.list_ctrl.GetItem(itemId=row, col=36)
    ALT = SetMaxLength(item.GetText(), 10)
        
    item = self.list_ctrl.GetItem(itemId=row, col=37)
    EEDate = SetMaxLength(item.GetText(), 8)
        
    item = self.list_ctrl.GetItem(itemId=row, col=38)
    NENAreserved = SetMaxLength(item.GetText(), 81)
        
    item = self.list_ctrl.GetItem(itemId=row, col=39)
    CID2 = SetMaxLength(item.GetText(), 5)
        
    item = self.list_ctrl.GetItem(itemId=row, col=40)
    reserved2 = SetMaxLength(item.GetText(), 31)
        
    item = self.list_ctrl.GetItem(itemId=row, col=41)
    EOR = SetMaxLength(item.GetText(), 1)


    lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
        PoDir + community + ST + location + customername + CLS + TOS +   \
        XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
        SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
        Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
        NENAreserved + CID2 + reserved2 + EOR

        
    #print len(lineout)
    #print lineout

    return lineout


######################################################################
def GetText_from_ALI_columns_currRow_OLV(self, row):

        lineout = []
        
        item = self.dataOlv.GetItemText(row, 0)
        FOC = SetMaxLength(item, 1)
        #print "FOC = [%s]   length = %d\n" % (FOC, len(FOC))
        

        item = self.dataOlv.GetItemText(row, 1)
        NPA = SetMaxLength(item, 3)
        #print "NPA = [%s]   length = %d\n" % (NPA, len(NPA))
        
        item = self.dataOlv.GetItemText(row, 2)
        TN = SetMaxLength(item, 7)
        #print "TN = [%s]   length = %d\n" % (TN, len(TN))

        
        item = self.dataOlv.GetItemText(row, 3)
        HNum = SetMaxLength(item, 10)
        #print "HNum = [%s]  -  length = %s\n" % (HNum, len(HNum))
        
        item = self.dataOlv.GetItemText(row, 4)
        HNumSuffix = SetMaxLength(item, 4)
        #print "HNumSuffix = [%s]   length = %d\n" % (HNumSuffix, len(HNumSuffix))

        
        item = self.dataOlv.GetItemText(row, 5)
        PrDir = SetMaxLength(item, 2)
        #print "PrDir = [%s]   length = %d\n" % (PrDir, len(PrDir))

        item = self.dataOlv.GetItemText(row, 6)
        streetname = SetMaxLength(item, 60)
        #print "streetname = [%s]  -  length = %s\n" % (streetname, len(streetname))
        
        item = self.dataOlv.GetItemText(row, 7)
        SSfx = SetMaxLength(item, 4)
        #print "SSfx = [%s]   length = %d\n" % (SSfx, len(SSfx))

        
        item = self.dataOlv.GetItemText(row, 8)
        PoDir = SetMaxLength(item, 2)
        #print "PoDir = [%s]   length = %d\n" % (PoDir, len(PoDir))


        item = self.dataOlv.GetItemText(row, 9)
        community = SetMaxLength(item, 32)
        #print "community = [%s]   length = %d\n" % (community, len(community))
        
        item = self.dataOlv.GetItemText(row, 10)
        ST =  SetMaxLength(item, 2)
        #print "ST = [%s]   length = %d\n" % (ST, len(ST))
        
        item = self.dataOlv.GetItemText(row, 11)
        location = SetMaxLength(item, 60)
        #print "location = [%s]   length = %d\n" % (location, len(location))
        
        item = self.dataOlv.GetItemText(row, 12)
        customername = SetMaxLength(item, 32)
        #print "customername = [%s]   length = %d\n" % (customername, len(customername))
        
        item = self.dataOlv.GetItemText(row, 13)
        CLS = SetMaxLength(item, 1)
        #print "CLS = [%s]   length = %d\n" % (CLS, len(CLS))
        
        item = self.dataOlv.GetItemText(row, 14)
        TOS = SetMaxLength(item, 1)
        #print "TOS = [%s]   length = %d\n" % (TOS, len(TOS))
        
        item = self.dataOlv.GetItemText(row, 15)
        XCH = SetMaxLength(item, 4)
        #print "XCH = [%s]   length = %d\n" % (XCH, len(XCH))
        
        item = self.dataOlv.GetItemText(row, 16)
        ESN = SetMaxLength(item, 5)
        #print "ESN = [%s]   length = %d\n" % (ESN, len(ESN))
        
        item = self.dataOlv.GetItemText(row, 17)
        MNPA = SetMaxLength(item, 3)
        #print "MNPA = [%s]   length = %d\n" % (MNPA, len(MNPA))
        
        item = self.dataOlv.GetItemText(row, 18)
        Main = SetMaxLength(item, 7)
        #print "Main = [%s]   length = %d\n" % (Main, len(Main))
        
        item = self.dataOlv.GetItemText(row, 19)
        OrderNo = SetMaxLength(item, 10)
        #print "OrderNo = [%s]   length = %d\n" % (OrderNo, len(OrderNo))
        
        item = self.dataOlv.GetItemText(row, 20)
        ExDate = SetMaxLength(item, 6)
        #print "ExDate = [%s]   length = %d\n" % (ExDate, len(ExDate))
        
        item = self.dataOlv.GetItemText(row, 21)
        COID = SetMaxLength(item, 4)
        #print "COID = [%s]   length = %d\n" % (COID, len(COID))
        
        item = self.dataOlv.GetItemText(row, 22)
        CID1 = SetMaxLength(item, 5)
        #print "CID1 = [%s]   length = %d\n" % (CID1, len(CID1))
        
        item = self.dataOlv.GetItemText(row, 23)
        SID = SetMaxLength(item, 1)
        #print "SID = [%s]   length = %d\n" % (SID, len(SID))
        
        item = self.dataOlv.GetItemText(row, 24)
        ZIP = SetMaxLength(item, 5)
        #print "ZIP = [%s]   length = %d\n" % (ZIP, len(ZIP))
        
        item = self.dataOlv.GetItemText(row, 25)
        ZIP4 = SetMaxLength(item, 4)
        #print "ZIP4= [%s]   length = %d\n" % (ZIP4, len(ZIP4))
        
        item = self.dataOlv.GetItemText(row, 26)
        general = SetMaxLength(item, 11)
        #print "general = [%s]   length = %d\n" % (general, len(general))
        
        item = self.dataOlv.GetItemText(row, 27)
        CCD = SetMaxLength(item, 3)
        #print "CCD = [%s]   length = %d\n" % (CCD, len(CCD))
        
        item = self.dataOlv.GetItemText(row, 28)
        comments = SetMaxLength(item, 30)
        #print "comments = [%s]   length = %d\n" % (comments, len(comments))
        
        item = self.dataOlv.GetItemText(row, 29)
        XLON = SetMaxLength(item, 9)
        #print "XLON = [%s]   length = %d\n" % (XLON, len(XLON))
        
        item = self.dataOlv.GetItemText(row, 30)
        YLAT = SetMaxLength(item, 9)
        #print "YLAT = [%s]   length = %d\n" % (YLAT, len(YLAT))
        
        item = self.dataOlv.GetItemText(row, 31)
        Zcoord = SetMaxLength(item, 5)
        #print "Zcoord = [%s]   length = %d\n" % (Zcoord, len(Zcoord))
        
        item = self.dataOlv.GetItemText(row, 32)
        CellID = SetMaxLength(item, 6)
        #print "CellID = [%s]   length = %d\n" % (CellID, len(CellID))
        
        item = self.dataOlv.GetItemText(row, 33)
        SecID = SetMaxLength(item, 1)
        #print "SecID = [%s]   length = %d\n" % (SecID, len(SecID))
        
        item = self.dataOlv.GetItemText(row, 34)
        TAR = SetMaxLength(item, 6)
        #print "TAR = [%s]   length = %d\n" % (TAR, len(TAR))
        
        item = self.dataOlv.GetItemText(row, 35)
        reserved1 = SetMaxLength(item, 21)
        #print "reserved1 = [%s]   length = %d\n" % (reserved1, len(reserved1))
        
        item = self.dataOlv.GetItemText(row, 36)
        ALT = SetMaxLength(item, 10)
        #print "ALT = [%s]   length = %d\n" % (ALT, len(ALT))
        
        item = self.dataOlv.GetItemText(row, 37)
        EEDate = SetMaxLength(item, 8)
        #print "EEDate = [%s]   length = %d\n" % (EEDate, len(EEDate))
        
        item = self.dataOlv.GetItemText(row, 38)
        NENAreserved = SetMaxLength(item, 81)
        #print "NENAreserved = [%s]   length = %d\n" % (NENAreserved, len(NENAreserved))
        
        item = self.dataOlv.GetItemText(row, 39)
        CID2 = SetMaxLength(item, 5)
        #print "CID2 = [%s]   length = %d\n" % (CID2, len(CID2))
        
        item = self.dataOlv.GetItemText(row, 40)
        reserved2 = SetMaxLength(item, 31)
        #print "reserved2 = [%s]   length = %d\n" % (reserved2, len(reserved2))
        
        item = self.dataOlv.GetItemText(row, 41)
        EOR = SetMaxLength(item, 1)
        #print "EOR = [%s]   length = %d\n" % (EOR, len(EOR))

        lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
            PoDir + community + ST + location + customername + CLS + TOS +   \
            XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
            SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
            Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
            NENAreserved + CID2 + reserved2 + EOR

        
        #print len(lineout)
        #print lineout
        
        return lineout



#######################################################################
#def GetText_from_ALI_columns_currRow_OLV_OLD(self, row):

#        lineout = []
        
#        item = self.dataOlv.GetItem(itemId=row, col=0)
#        FOC = SetMaxLength(item.GetText(), 1)
#        #print "FOC = [%s]\n" % FOC

#        item = self.dataOlv.GetItem(itemId=row, col=1)
#        NPA = SetMaxLength(item.GetText(), 3)
#        #print "NPA = [%s]\n" % NPA
        
#        item = self.dataOlv.GetItem(itemId=row, col=2)
#        TN = SetMaxLength(item.GetText(), 7)
#        #print "TN = [%s]\n" % TN
        
#        item = self.dataOlv.GetItem(itemId=row, col=3)
#        HNum = SetMaxLength(item.GetText(), 10)
#        #print "HNum = [%s]  -  length = %s\n" % (HNum, len(HNum))
        
#        item = self.dataOlv.GetItem(itemId=row, col=4)
#        HNumSuffix = SetMaxLength(item.GetText(), 4)
        
#        item = self.dataOlv.GetItem(itemId=row, col=5)
#        PrDir = SetMaxLength(item.GetText(), 2)
        
#        item = self.dataOlv.GetItem(itemId=row, col=6)
#        streetname = SetMaxLength(item.GetText(), 60)
#        #print "streetname = [%s]  -  length = %s\n" % (streetname, len(streetname))
        
#        item = self.dataOlv.GetItem(itemId=row, col=7)
#        SSfx = SetMaxLength(item.GetText(), 4)
        
#        item = self.dataOlv.GetItem(itemId=row, col=8)
#        PoDir = SetMaxLength(item.GetText(), 2)
        
#        item = self.dataOlv.GetItem(itemId=row, col=9)
#        community = SetMaxLength(item.GetText(), 32)
        
#        item = self.dataOlv.GetItem(itemId=row, col=10)
#        ST =  SetMaxLength(item.GetText(), 2)
        
#        item = self.dataOlv.GetItem(itemId=row, col=11)
#        location = SetMaxLength(item.GetText(), 60)
        
#        item = self.dataOlv.GetItem(itemId=row, col=12)
#        customername = SetMaxLength(item.GetText(), 32)
        
#        item = self.dataOlv.GetItem(itemId=row, col=13)
#        CLS = SetMaxLength(item.GetText(), 1)
        
#        item = self.dataOlv.GetItem(itemId=row, col=14)
#        TOS = SetMaxLength(item.GetText(), 1)
        
#        item = self.dataOlv.GetItem(itemId=row, col=15)
#        XCH = SetMaxLength(item.GetText(), 4)
        
#        item = self.dataOlv.GetItem(itemId=row, col=16)
#        ESN = SetMaxLength(item.GetText(), 5)
        
#        item = self.dataOlv.GetItem(itemId=row, col=17)
#        MNPA = SetMaxLength(item.GetText(), 3)
        
#        item = self.dataOlv.GetItem(itemId=row, col=18)
#        Main = SetMaxLength(item.GetText(), 7)
        
#        item = self.dataOlv.GetItem(itemId=row, col=19)
#        OrderNo = SetMaxLength(item.GetText(), 10)
        
#        item = self.dataOlv.GetItem(itemId=row, col=20)
#        ExDate = SetMaxLength(item.GetText(), 6)
        
#        item = self.dataOlv.GetItem(itemId=row, col=21)
#        COID = SetMaxLength(item.GetText(), 4)
        
#        item = self.dataOlv.GetItem(itemId=row, col=22)
#        CID1 = SetMaxLength(item.GetText(), 5)
        
#        item = self.dataOlv.GetItem(itemId=row, col=23)
#        SID = SetMaxLength(item.GetText(), 1)
        
#        item = self.dataOlv.GetItem(itemId=row, col=24)
#        ZIP = SetMaxLength(item.GetText(), 5)
        
#        item = self.dataOlv.GetItem(itemId=row, col=25)
#        ZIP4 = SetMaxLength(item.GetText(), 4)
        
#        item = self.dataOlv.GetItem(itemId=row, col=26)
#        general = SetMaxLength(item.GetText(), 11)
        
#        item = self.dataOlv.GetItem(itemId=row, col=27)
#        CCD = SetMaxLength(item.GetText(), 3)
        
#        item = self.dataOlv.GetItem(itemId=row, col=28)
#        comments = SetMaxLength(item.GetText(), 30)
        
#        item = self.dataOlv.GetItem(itemId=row, col=29)
#        XLON = SetMaxLength(item.GetText(), 9)
        
#        item = self.dataOlv.GetItem(itemId=row, col=30)
#        YLAT = SetMaxLength(item.GetText(), 9)
        
#        item = self.dataOlv.GetItem(itemId=row, col=31)
#        Zcoord = SetMaxLength(item.GetText(), 5)
        
#        item = self.dataOlv.GetItem(itemId=row, col=32)
#        CellID = SetMaxLength(item.GetText(), 6)
        
#        item = self.dataOlv.GetItem(itemId=row, col=33)
#        SecID = SetMaxLength(item.GetText(), 1)
        
#        item = self.dataOlv.GetItem(itemId=row, col=34)
#        TAR = SetMaxLength(item.GetText(), 6)
        
#        item = self.dataOlv.GetItem(itemId=row, col=35)
#        reserved1 = SetMaxLength(item.GetText(), 21)
        
#        item = self.dataOlv.GetItem(itemId=row, col=36)
#        ALT = SetMaxLength(item.GetText(), 10)
        
#        item = self.dataOlv.GetItem(itemId=row, col=37)
#        EEDate = SetMaxLength(item.GetText(), 8)
        
#        item = self.dataOlv.GetItem(itemId=row, col=38)
#        NENAreserved = SetMaxLength(item.GetText(), 81)
        
#        item = self.dataOlv.GetItem(itemId=row, col=39)
#        CID2 = SetMaxLength(item.GetText(), 5)
        
#        item = self.dataOlv.GetItem(itemId=row, col=40)
#        reserved2 = SetMaxLength(item.GetText(), 31)
        
#        item = self.dataOlv.GetItem(itemId=row, col=41)
#        EOR = SetMaxLength(item.GetText(), 1)


#        lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
#            PoDir + community + ST + location + customername + CLS + TOS +   \
#            XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
#            SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
#            Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
#            NENAreserved + CID2 + reserved2 + EOR

        
#        print len(lineout)
#        print lineout

#        return lineout

######################################################################    
def SaveEditedDatFileNameAs(lineout):    
    """ Save edited file """
    try:
        # Save away the edited text        
        dlg = wx.FileDialog(
                    None, message="Save file as ...",
                    defaultDir=".",
                    defaultFile="", wildcard="*.dat", style=wx.SAVE
                    )

        if dlg.ShowModal() == wx.ID_OK:       

                # Open the file for write, write, close
                filename = dlg.GetFilename()
                dirname = dlg.GetDirectory()

                filehandle = open(os.path.join(dirname, filename),'w')

                filehandle.write(lineout)
                filehandle.close()

        # Get rid of the dialog to keep things tidy
        dlg.Destroy()
    except:
        print "Exception in SaveEditedDatFileNameAs"


##########################################################################
def MSAG_read_in_chunks(file_object, chunk_size=(MSAG_REC_LEN + 1)):
    """
    Best method is to use iter & yield.

    'yield' is the keyword in python used for generator expressions.
    That means that the next time the function is called (or iterated on),
    the execution will start back up at the exact point it left off
    last time you called it.
    """
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


########################################################################
def obtain_MSAG_fields_from_line(line):
    """
    obtain MSAG fields name from data line
    """
    line.strip('\n')

    PrDir      = line[0:2]            #edit1   col 1-2
    streetname = line[2:62]           #edit2   col 3-62
    StSffx     = line[62:66]          #edit3   col 63-66
    PoDir      = line[66:68]          #edit4   col 67-68
    Low        = line[68:78]          #edit5   col 69-78
    High       = line[78:88]          #edit6   col 79-88
    MSAGcomm   = line[88:120]         #edit7   col 89-120
    ST         = line[120:122]        #edit8   col 121-122
    oddeven    = line[122]            #edit9   col 123
    ESN        = line[123:128]        #edit10  col 124-128
    ExDate     = line[128:134]        #edit11  col 129-134
    PSAPid     = line[134:138]        #edit12  col 135-138
    COID       = line[138:142]        #edit13  col 139-142
    XCH        = line[142:146]        #edit14  col 143-146
    general    = line[146:166]        #edit15  col 147-166
    TAR        = line[166:172]        #edit16  col 167-172
    FOC        = line[172]            #edit17  col 173
    reserved   = line[173:191]        #edit18  col 174-191
    EExDate    = line[191:199]        #edit19  col 192-199
    EOR        = line[199]            #edit20  col 200
            
    return  PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
              ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR


########################################################################
def Read_from_MSAG_file_OLV():

    prefixed = ''
    extension_list = ['dat', 'DAT']
    selected_ALI_datfilename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
    selectedpath, selectedfile = selected_ALI_datfilename

    currpath = selectedpath + "\\" + selectedfile
           
    if (os.path.exists(currpath)):
        dline = {}
        reccount = 0
        
        start = time.time()                              # start the stopwatch
        print "start timing:  %f" % start
        time.clock()

        # max = number higher than estimated number of records loading from file
        #max = MAX_PROGRESS        
        count = 0
        keepGoing = True       
        pdlg = wx.ProgressDialog("Loading data",
                           "Loading data from file",
                           maximum = MAX_PROGRESS,
                           parent=None,
                           style = wx.PD_CAN_ABORT |
                             wx.PD_APP_MODAL |
                              wx.PD_ELAPSED_TIME
                            | wx.PD_AUTO_HIDE
                            | wx.PD_REMAINING_TIME
                            )
        
        dfile = open(currpath, 'r')
        for line in MSAG_read_in_chunks(dfile):
            retvar = process_data_chunk(line, dline, reccount)
            dline, reccount = retvar

            try:
                # start progress dialog
                while keepGoing and count <= reccount:
                    count += 1
                    wx.MilliSleep(1)
                    (keepGoing, skip) = pdlg.Update(count)
            except:
                #print "Exception in progress dialog"
                pdlg.Destroy()

        # close progress dialog
        keepGoing = False
        pdlg.Destroy()
                            
        elapsedtime = time.time() - start          # end timing
        print "end timing:  %f" % elapsedtime
        
        dfile.close()

    #print "reccount = %s\n" % reccount

    rcnt = 1
    #finally have data line dictionary
    for key in sorted(dline):
        if dline.has_key(str(key)):            
            line = dline[str(key)]            
            rcnt += 1
        else:
            print 'NONE'

    return line, dline, reccount, selectedpath, selectedfile, currpath,elapsedtime


########################################################################
def Read_from_MSAG_file():

    prefixed = ''
    extension_list = ['dat', 'DAT']
    selected_ALI_datfilename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
    selectedpath, selectedfile = selected_ALI_datfilename

    currpath = selectedpath + "\\" + selectedfile
           
    if (os.path.exists(currpath)):
        dline = {}
        reccount = 0
        
        start = time.time()                              # start the stopwatch
        print "start timing:  %f" % start
        time.clock()

        # max = number higher than estimated number of records loading from file
        #max = MAX_PROGRESS        
        count = 0
        keepGoing = True       
        pdlg = wx.ProgressDialog("Loading data",
                           "Loading data from file",
                           maximum = MAX_PROGRESS,
                           parent=None,
                           style = wx.PD_CAN_ABORT |
                             wx.PD_APP_MODAL |
                              wx.PD_ELAPSED_TIME
                            | wx.PD_AUTO_HIDE
                            | wx.PD_REMAINING_TIME
                            )
        
        dfile = open(currpath, 'r')
        for line in MSAG_read_in_chunks(dfile):
            retvar = process_data_chunk(line, dline, reccount)
            dline, reccount = retvar

            try:
                # start progress dialog
                while keepGoing and count < reccount:
                    count += 1
                    wx.MilliSleep(1)
                    (keepGoing, skip) = pdlg.Update(count)
            except:
                print "Exception in progress dialog"
                pdlg.Destroy()

        # close progress dialog
        keepGoing = False
        pdlg.Destroy()
                            
        elapsedtime = time.time() - start          # end timing
        print "end timing:  %f" % elapsedtime
        
        dfile.close()

    #print "reccount = %s\n" % reccount

    rcnt = 1
    #finally have data line dictionary
    for key in sorted(dline):
        if dline.has_key(str(key)):            
            line = dline[str(key)]            
            rcnt += 1
        else:
            print 'NONE'

    return dline, reccount, selectedpath, selectedfile, currpath,elapsedtime


########################################################################

def insert_MSAG_column_to_list_ctrl(self):
        """
                 PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
                ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR
        """
        # insert columns to self.list_ctrl
        self.list_ctrl.InsertColumn(0, "Prefix Directional  (Col: 1 - 2, max = 2)")
        self.list_ctrl.InsertColumn(1, "Street Name  (Col: 3 - 62, max = 60)")
        self.list_ctrl.InsertColumn(2, "Street Suffix  (Col: 63 - 66, max = 4)")
        self.list_ctrl.InsertColumn(3, "Post Directory  (Col: 67 - 68, max = 2)")
        self.list_ctrl.InsertColumn(4, "Low Range  (Col: 69 - 78, max = 10)")
        self.list_ctrl.InsertColumn(5, "High Range  (Col: 79 - 88, max = 10)")
        self.list_ctrl.InsertColumn(6, "MSAG Community  (Col: 89 - 120, max = 32)")
        self.list_ctrl.InsertColumn(7, "State  (Col: 121 - 122, max = 2)")
        self.list_ctrl.InsertColumn(8, "Odd-Even  (Col: 123, max = 1)")
        self.list_ctrl.InsertColumn(9, "ESN  (Col: 124 - 128, max = 5)")
        self.list_ctrl.InsertColumn(10, "Extract Date  (Col: 129 - 134, max = 6)")
        self.list_ctrl.InsertColumn(11, "PSAP ID  (Col: 135 - 138, max = 4)")
        self.list_ctrl.InsertColumn(12, "County ID  (Col: 139 - 142, max = 4)")
        self.list_ctrl.InsertColumn(13, "Exchange  (Col: 143 - 146, max = 4)")
        self.list_ctrl.InsertColumn(14, "General Use  (Col: 147 - 166, max = 4)")
        self.list_ctrl.InsertColumn(15, "TAR Code  (Col: 167 - 172, max = 6)")
        self.list_ctrl.InsertColumn(16, "Function of Change  (Col: 173, max = 1)")
        self.list_ctrl.InsertColumn(17, "Reserved  (Col: 174 - 191, max = 18)")
        self.list_ctrl.InsertColumn(18, "Expanded Extracted Date  (Col: 192 - 199, max = 8")
        self.list_ctrl.InsertColumn(19, "EOR  (Col: 200, max = 1)")   


##################################################################
def insert_string_MSAG_items_to_list_ctrl(self, index,PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
                ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR):
    
        self.list_ctrl.InsertStringItem(index, PrDir)
        self.list_ctrl.SetStringItem(index, 1, streetname)
        self.list_ctrl.SetStringItem(index, 2, StSffx)
        self.list_ctrl.SetStringItem(index, 3, PoDir)
        self.list_ctrl.SetStringItem(index, 4, Low)
        self.list_ctrl.SetStringItem(index, 5, High)
        self.list_ctrl.SetStringItem(index, 6, MSAGcomm)
        self.list_ctrl.SetStringItem(index, 7, ST)
        self.list_ctrl.SetStringItem(index, 8, oddeven)
        self.list_ctrl.SetStringItem(index, 9, ESN)
        self.list_ctrl.SetStringItem(index, 10, ExDate)
        self.list_ctrl.SetStringItem(index, 11, PSAPid)
        self.list_ctrl.SetStringItem(index, 12, COID)
        self.list_ctrl.SetStringItem(index, 13, XCH)
        self.list_ctrl.SetStringItem(index, 14, general)
        self.list_ctrl.SetStringItem(index, 15, TAR)
        self.list_ctrl.SetStringItem(index, 16, FOC)
        self.list_ctrl.SetStringItem(index, 17, reserved)
        self.list_ctrl.SetStringItem(index, 18, EExDate)
        self.list_ctrl.SetStringItem(index, 19, EOR)


######################################################################
def GetText_from_MSAG_columns_currRow(self, row):
        lineout = []
                
        item = self.list_ctrl.GetItem(itemId=row, col=0)
        PrDir = SetMaxLength(item.GetText(), 2)
        
        item = self.list_ctrl.GetItem(itemId=row, col=1)
        streetname = SetMaxLength(item.GetText(), 60)
        
        item = self.list_ctrl.GetItem(itemId=row, col=2)
        StSffx = SetMaxLength(item.GetText(), 4)

        item = self.list_ctrl.GetItem(itemId=row, col=3)
        PoDir = SetMaxLength(item.GetText(), 2)
        
        item = self.list_ctrl.GetItem(itemId=row, col=4)
        Low = SetMaxLength(item.GetText(), 10)
        
        item = self.list_ctrl.GetItem(itemId=row, col=5)
        High = SetMaxLength(item.GetText(), 10)
        
        item = self.list_ctrl.GetItem(itemId=row, col=6)
        MSAGcomm = SetMaxLength(item.GetText(), 32)
        
        item = self.list_ctrl.GetItem(itemId=row, col=7)
        ST = SetMaxLength(item.GetText(), 2)
        
        item = self.list_ctrl.GetItem(itemId=row, col=8)
        oddeven = SetMaxLength(item.GetText(), 1)
        
        item = self.list_ctrl.GetItem(itemId=row, col=9)
        ESN = SetMaxLength(item.GetText(), 5)
        
        item = self.list_ctrl.GetItem(itemId=row, col=10)
        ExDate = SetMaxLength(item.GetText(), 6)
        
        item = self.list_ctrl.GetItem(itemId=row, col=11)
        PSAPid = SetMaxLength(item.GetText(), 4)
        
        item = self.list_ctrl.GetItem(itemId=row, col=12)
        COID = SetMaxLength(item.GetText(), 4)
        
        item = self.list_ctrl.GetItem(itemId=row, col=13)
        XCH = SetMaxLength(item.GetText(), 4)
        
        item = self.list_ctrl.GetItem(itemId=row, col=14)
        general = SetMaxLength(item.GetText(), 20)
        
        item = self.list_ctrl.GetItem(itemId=row, col=15)
        TAR = SetMaxLength(item.GetText(), 6)
        
        item = self.list_ctrl.GetItem(itemId=row, col=16)
        FOC = SetMaxLength(item.GetText(), 1)
        
        item = self.list_ctrl.GetItem(itemId=row, col=17)
        reserved = SetMaxLength(item.GetText(), 18)
        
        item = self.list_ctrl.GetItem(itemId=row, col=18)
        EExDate = SetMaxLength(item.GetText(), 8)

        
        item = self.list_ctrl.GetItem(itemId=row, col=19)
        EOR = SetMaxLength(item.GetText(), 1)

        
        lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                    ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                    TAR + FOC + reserved + EExDate + EOR
        
        print len(lineout)
        print lineout

        return lineout


##############################################
def GetText_from_MSAG_columns_currRow_OLV(self, row):

        lineout = []
                
        item = self.dataOlv.GetItem(itemId=row, col=0)
        PrDir = SetMaxLength(item.GetText(), 2)
        
        item = self.dataOlv.GetItem(itemId=row, col=1)
        streetname = SetMaxLength(item.GetText(), 60)
        
        item = self.dataOlv.GetItem(itemId=row, col=2)
        StSffx = SetMaxLength(item.GetText(), 4)

        item = self.dataOlv.GetItem(itemId=row, col=3)
        PoDir = SetMaxLength(item.GetText(), 2)
        
        item = self.dataOlv.GetItem(itemId=row, col=4)
        Low = SetMaxLength(item.GetText(), 10)
        
        item = self.dataOlv.GetItem(itemId=row, col=5)
        High = SetMaxLength(item.GetText(), 10)
        
        item = self.dataOlv.GetItem(itemId=row, col=6)
        MSAGcomm = SetMaxLength(item.GetText(), 32)
        
        item = self.dataOlv.GetItem(itemId=row, col=7)
        ST = SetMaxLength(item.GetText(), 2)
        
        item = self.dataOlv.GetItem(itemId=row, col=8)
        oddeven = SetMaxLength(item.GetText(), 1)
        
        item = self.dataOlv.GetItem(itemId=row, col=9)
        ESN = SetMaxLength(item.GetText(), 5)
        
        item = self.dataOlv.GetItem(itemId=row, col=10)
        ExDate = SetMaxLength(item.GetText(), 6)
        
        item = self.dataOlv.GetItem(itemId=row, col=11)
        PSAPid = SetMaxLength(item.GetText(), 4)
        
        item = self.dataOlv.GetItem(itemId=row, col=12)
        COID = SetMaxLength(item.GetText(), 4)
        
        item = self.dataOlv.GetItem(itemId=row, col=13)
        XCH = SetMaxLength(item.GetText(), 4)
        
        item = self.dataOlv.GetItem(itemId=row, col=14)
        general = SetMaxLength(item.GetText(), 20)
        
        item = self.dataOlv.GetItem(itemId=row, col=15)
        TAR = SetMaxLength(item.GetText(), 6)
        
        item = self.dataOlv.GetItem(itemId=row, col=16)
        FOC = SetMaxLength(item.GetText(), 1)
        
        item = self.dataOlv.GetItem(itemId=row, col=17)
        reserved = SetMaxLength(item.GetText(), 18)
        
        item = self.dataOlv.GetItem(itemId=row, col=18)
        EExDate = SetMaxLength(item.GetText(), 8)

        
        item = self.dataOlv.GetItem(itemId=row, col=19)
        EOR = SetMaxLength(item.GetText(), 1)

        
        lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                    ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                    TAR + FOC + reserved + EExDate + EOR
        
        #print len(lineout)
        #print lineout

        return lineout


######################################################################
def GetText_from_MSAG_columns_currRow_OLV_3(self, row):

        lineout = []
        # ignore the check status column 0
        
        item = self.dataOlv.GetItemText(row, 1)
        PrDir = SetMaxLength(item, 2)
        
        item = self.dataOlv.GetItemText(row, 2)
        streetname = SetMaxLength(item, 60)
        
        item = self.dataOlv.GetItemText(row, 3)
        StSffx = SetMaxLength(item, 4)

        item = self.dataOlv.GetItemText(row, 4)
        PoDir = SetMaxLength(item, 2)
        
        item = self.dataOlv.GetItemText(row, 5)
        Low = SetMaxLength(item, 10)
        
        item = self.dataOlv.GetItemText(row, 6)
        High = SetMaxLength(item, 10)
        
        item = self.dataOlv.GetItemText(row, 7)
        MSAGcomm = SetMaxLength(item, 32)
        
        item = self.dataOlv.GetItemText(row, 8)
        ST = SetMaxLength(item, 2)
        
        item = self.dataOlv.GetItemText(row, 9)
        oddeven = SetMaxLength(item, 1)
        
        item = self.dataOlv.GetItemText(row, 10)
        ESN = SetMaxLength(item, 5)
        
        item = self.dataOlv.GetItemText(row, 11)
        ExDate = SetMaxLength(item, 6)
        
        item = self.dataOlv.GetItemText(row, 12)
        PSAPid = SetMaxLength(item, 4)
        
        item = self.dataOlv.GetItemText(row, 13)
        COID = SetMaxLength(item, 4)
        
        item = self.dataOlv.GetItemText(row, 14)
        XCH = SetMaxLength(item, 4)
        
        item = self.dataOlv.GetItemText(row, 15)
        general = SetMaxLength(item, 20)
        
        item = self.dataOlv.GetItemText(row, 16)
        TAR = SetMaxLength(item, 6)
        
        item = self.dataOlv.GetItemText(row, 17)
        FOC = SetMaxLength(item, 1)
        
        item = self.dataOlv.GetItemText(row, 18)
        reserved = SetMaxLength(item, 18)
        
        item = self.dataOlv.GetItemText(row, 19)
        EExDate = SetMaxLength(item, 8)

        
        item = self.dataOlv.GetItemText(row, 20)
        EOR = SetMaxLength(item, 1)

        
        lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                    ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                    TAR + FOC + reserved + EExDate + EOR
        
        #print len(lineout)
        #print lineout
        
        return lineout


class Edit_Existing_MSAG_SO_Dialog(wx.Dialog):
    """
    Load only one existing MSAG record
    """
    def __init__(self, parent, id=-1, title="MSAG SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(780, 580))
                
        self.SetBackgroundColour((255,228,196))  # bisque
        
        # for display common messages on this dialog
        julianday = SO_utils.get_julianday()

        line = []       
        loaded = Load_MSAG_SO_File()
        line, selectedpath, selectedfile  = loaded

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 250), size=wx.Size(185, 20))
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Editing  [%s]  in  [%s]     -     Today Julian's date is   %s\n" % (selectedfile, selectedpath, julianday))

        
##        print "line = [%s]\n" % line
        print len(line)

        if (len(line) == MSAG_REC_LENGTH):  

            PrDir      = line[0:2]            #edit1   col 1-2
            streetname = line[2:62]           #edit2   col 3-62
            StSffx     = line[62:66]          #edit3   col 63-66
            PoDir      = line[66:68]          #edit4   col 67-68
            Low        = line[68:78]          #edit5   col 69-78
            High       = line[78:88]          #edit6   col 79-88
            MSAGcomm   = line[88:120]         #edit7   col 89-120
            ST         = line[120:122]        #edit8   col 121-122
            oddeven    = line[122]            #edit9   col 123
            ESN        = line[123:128]        #edit10  col 124-128
            ExDate     = line[128:134]        #edit11  col 129-134
            PSAPid     = line[134:138]        #edit12  col 135-138
            COID       = line[138:142]        #edit13  col 139-142
            XCH        = line[142:146]        #edit14  col 143-146
            general    = line[146:166]        #edit15  col 147-166
            TAR        = line[166:172]        #edit16  col 167-172
            FOC        = line[172]            #edit17  col 173
            reserved   = line[173:191]        #edit18  col 174-191
            EExDate    = line[191:199]        #edit19  col 192-199
            EOR        = line[199]            #edit20  col 200

            ## remove trailing spaces
            #PrDir.strip()
            #streetname.strip()
            #StSffx.strip()
            #PoDir.strip()
            #Low.strip()
            #High.strip()
            #MSAGcomm.strip()
            #oddeven.strip()
            #ESN.strip()
            #ExDate.strip()
            #PSAPid.strip()
            #COID.strip()
            #XCH.strip()
            #general.strip()
            #TAR.strip()
            #FOC.strip()
            #reserved.strip()
            #EExDate.strip()
            #EOR.strip()        

            Display_single_MSAG_record_with_data(self, PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,     \
                                                       XCH,general,TAR,FOC,reserved,EExDate,EOR)

        
            self.button1 = wx.Button(self, wx.ID_OK, label="SAVE modified MSAG SOI data file",
                pos=wx.Point(180, 300), size=wx.Size(185, 28))
            prompt = "SAVE modified MSAG SOI data file"
            self.button1.SetToolTip(wx.ToolTip(prompt)) 
            self.button1.SetBackgroundColour((217,255,219)) # vegaseat green

            self.button2 = wx.Button(self, wx.ID_CANCEL, label="Cancel",
                pos=wx.Point(420, 300), size=wx.Size(140, 28))
            prompt = "Cancel saving modified MSAG SOI data file"
            self.button2.SetToolTip(wx.ToolTip(prompt)) 
            self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
            # enter to tab, move to next field
            return_id = wx.NewId()
            acc_table = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, return_id)])
            self.SetAcceleratorTable(acc_table)
            wx.EVT_MENU(self, return_id, self.on_return)


            # respond to button click event
            self.button1.Bind(wx.EVT_BUTTON, self.button1Click, self.button1)

            # respond to button click event
            self.button2.Bind(wx.EVT_BUTTON, self.onCancel, self.button2)

        else:
            if (len(line) <> 0):
                SO_utils.display_msg("Invalid or corrupted data file loaded in Edit MSAG SOI data file", "Edit MSAG SOI data file")
            self.Destroy()   
       
    def button1Click(self,event):
        """SAVE modified ALI SO DAT file button has been clicked"""

        try:
            # string of record to build
            lineout = []

            PrDir = self.edit1.GetValue().ljust(2)
            streetname = self.edit2.GetValue().ljust(60)
            StSffx = self.edit3.GetValue().ljust(4)
            PoDir = self.edit4.GetValue().ljust(2)
            Low = self.edit5.GetValue().ljust(10)
            High = self.edit6.GetValue().ljust(10)
            MSAGcomm = self.edit7.GetValue().ljust(32)
            ST = self.edit8.GetValue().ljust(2)
            oddeven = self.edit9.GetValue().ljust(1)
            ESN = self.edit10.GetValue().ljust(5)
            ExDate = self.edit11.GetValue().ljust(6)
            PSAPid = self.edit12.GetValue().ljust(4)
            COID = self.edit13.GetValue().ljust(4)
            XCH = self.edit14.GetValue().ljust(4)
            general = self.edit15.GetValue().ljust(20)
            TAR = self.edit16.GetValue().ljust(6)
            FOC = self.edit17.GetValue().ljust(1)
            reserved = self.edit18.GetValue().ljust(18)
            EExDate = self.edit19.GetValue().ljust(8)
            EOR = self.edit20.GetValue().ljust(1)

            
            # building the record
            lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                      ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                      TAR + FOC + reserved + EExDate + EOR
                        
##            print "lineout = [%s]" % lineout
            print len(lineout)

            if ((len(lineout) == MSAG_REC_LENGTH) and (EOR == '*')):
                # Save edited file as
                SaveEditedDatFileNameAs(lineout)
                self.Destroy()
            else:
                print "Corrupted data record in Edit MSAG SOI dat file"
                SO_utils.display_msg("Corrupted data record in Edit MSAG SOI dat file", "Edit MSAG SOI data file")
                self.Destroy()
            
        except:
            print "Exception Button1click - Edit_MSAG_SO_Dialog"
            self.Destroy()

    

    def onCancel(self, event):
        self.result = None
        self.Destroy()
        
    def on_return(self, event):
        """
        Enter to tab, move to next field
        """
        ctl = wx.Window_FindFocus()
        ctl.Navigate()


class Edit_Existing_ALI_SO_Dialog(wx.Dialog):
    """
    Load only one existing record
    """
    def __init__(self, parent, id=-1, title="ALI SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(780, 580))
        
        self.SetBackgroundColour((255,228,196))  # bisque
        
        # for display common messages on this dialog
        julianday = SO_utils.get_julianday()

        line = []

        loaded = Load_ALI_SO_File()
        line, selectedpath, selectedfile = loaded

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(185, 20))
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Editing  [%s]  in  [%s]     -     Today Julian's date is   %s\n" % (selectedfile, selectedpath, julianday))

        #self.label4 = wx.StaticText(self, -1,
        #                    label="",
        #                    pos=wx.Point(325, 480), size=wx.Size(185, 20))
        #self.label4.SetForegroundColour((50,30,236))       # 225,40,82 = red
        #self.label4.SetLabel("Editing   s%\n" % selectedfile)
 
               
        #print "line = [%s]\n" % line
        print len(line)

        if (len(line) == ALI_REC_LENGTH):

            FOC     = line[0]               #FOC           edit1   1     col  1
            NPA     = line[1:4]            #NPA           edit2  3      col  2-4
            TN       = line[4:11]          #TN             edit3  7      col  5-11
            HNum  = line[11:21]        #HNum        edit4  10    col 12-21
            HNumSuffix = line[21:25]     #HNumSuffix   edit5  4     col 22-25
            PrDir     = line[25:27]        #PrDir        edit6  2       col 26-27
            streetname = line[27:87]   #streetname   edit7  60        col 28-87
            SSfx      = line[87:91]        #SSfx         edit8  4        col 88-91
            PoDir    = line[91:93]        #PoDir        edit9  2        col 92-93
            community  = line[93:125]     #community    edit10 32     col 94-125
            ST         = line[125:127]         #ST           edit11 2             col 126-127
            location   = line[127:187]      #location     edit12 60         col 128-187
            customername = line[187:219]      #customername edit13 32    col 188-219
            CLS       = line[219]                       #CLS          edit14 1      col 220
            TOS       = line[220]                       #TOS          edit15 1      col 221
            XCH      = line[221:225]                #XCH          edit16 4      col 222-225
            ESN       = line[225:230]                #ESN          edit17 5      col 226-230
            MNPA    = line[230:233]                #MNPA         edit18 3    col 231-233
            Main      = line[233:240]                #Main         edit19 7      col  234-240
            OrderNo = line[240:250]               #OrderNo      edit20 10    col 241-250
            ExDate   = line[250:256]               #ExDate       edit21 6      col  251-256
            COID      = line[256:260]               #COID         edit22 4      col 257-260
            CID1      = line[260:265]               #CID1         edit23 5       col 261-265
            SID        = line[265]                       #SID          edit24 1        col 266
            ZIP         = line[266:271]               #ZIP          edit25 5         col 267-271
            ZIP4       = line[271:275]               #ZIP4         edit26 4        col 272-275
            general   = line[275:286]               #general      edit27 11     col 276-286
            CCD       = line[286:289]                #CCD          edit28 3      col 287-289
            comments  = line[289:319]           #comments     edit29 30   col 290-319
            XLON     = line[319:328]               #XLON         edit30 9       col 320-328
            YLAT      = line[328:337]                #YLAT         edit31 9       col 329-337
            Zcoord   = line[337:342]               #Zcoord       edit32 5      col 338-342
            CellID     = line[342:348]               #CellID       edit33 6       col  343-348
            SecID     = line[348]                      #SecID        edit34 1       col  349
            TAR       = line[349:355]                #TAR          edit35 6       col 350-355
            reserved1 = line[355:376]             #reserved1    edit36 21    col  356-376
            ALT        = line[376:386]                #ALT          edit37 10      col  377-386
            EEDate    = line[386:394]              #EEDate       edit38 8       col  387-394
            NENAreserved  = line[394:475]     #NENAreserved edit39 81    col  395-475
            CID2       = line[475:480]              #CID2         edit40 5     col 476-480
            reserved2   = line[480:511]           #reserved2    edit41 31     col 481-511

            EOR        = line[511]                     #EOR          edit42 1 (*)      col 512

            # remove trailing spaces
            FOC.strip()
            NPA.strip()
            TN.strip()
            HNum.strip()
            HNumSuffix.strip()
            PrDir.strip()
            streetname.strip()
            SSfx.strip()
            PoDir.strip()
            community.strip()
            ST.strip()
            location.strip()
            customername.strip()
            CLS.strip()
            TOS.strip()
            XCH.strip()
            ESN.strip()
            MNPA.strip()
            Main.strip()
            OrderNo.strip()
            ExDate.strip()
            COID.strip()
            CID1.strip()
            SID.strip()
            ZIP.strip()
            ZIP4.strip()
            general.strip()
            CCD.strip()
            comments.strip()
            XLON.strip()
            YLAT.strip()
            Zcoord.strip()
            CellID.strip()
            SecID.strip()
            TAR.strip()
            reserved1.strip()
            ALT.strip()
            EEDate.strip()
            NENAreserved.strip()
            CID2.strip()
            reserved2.strip()
            EOR.strip()


            # fill in spaces max length allowed in fields   useless: they already have trailing spaces up to max length allowed (retrieve from file)
            FOC.ljust(1)
            NPA.ljust(3) 
            TN.ljust(7)
            HNum.ljust(10)
            HNumSuffix.ljust(4)
            
            PrDir.ljust(2)
            streetname.ljust(60)
            SSfx.ljust(4)
            
            PoDir.ljust(2)
            community.ljust(32)
            ST.ljust(2)
            
            location.ljust(60)
            customername.ljust(32)
            CLS.ljust(1)
            TOS.ljust(1)
            XCH.ljust(4)
            
            ESN.ljust(5)
            MNPA.ljust(3)
            Main.ljust(7)
            OrderNo.ljust(10)
            
            ExDate.ljust(6)
            COID.ljust(4)
            CID1.ljust(5)
            
            SID.ljust(1)
            ZIP.ljust(5)
            
            ZIP4.ljust(4)
            general.ljust(11)
            CCD.ljust(3)
            
            comments.ljust(30)
            XLON.ljust(9)
            YLAT.ljust(9)
            Zcoord.ljust(5)
            
            CellID.ljust(6)
            SecID.ljust(1)
            TAR.ljust(6)

            reserved1.ljust(21)
            ALT.ljust(10)
            
            EEDate.ljust(8)
            NENAreserved.ljust(81)
            CID2.ljust(5)
            reserved2.ljust(31)
            EOR.ljust(1)

            Display_single_ALI_record_with_data(self,FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
                                            MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                         \
                                            SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR)
                         
               
            self.button1 = wx.Button(self, wx.ID_OK, label="SAVE modified ALI SOI data file",
                pos=wx.Point(210, 500), size=wx.Size(185, 28))
            prompt = "SAVE modified ALI SOI data file"
            self.button1.SetToolTip(wx.ToolTip(prompt)) 
            self.button1.SetBackgroundColour((217,255,219)) # vegaseat green

            self.button2 = wx.Button(self, wx.ID_CANCEL, label="Cancel",
                pos=wx.Point(420, 500), size=wx.Size(140, 28))
            prompt = "Cancel saving modified ALI SOI data file"
            self.button2.SetToolTip(wx.ToolTip(prompt)) 
            self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
            # enter to tab, move to next field
            return_id = wx.NewId()
            acc_table = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, return_id)])
            self.SetAcceleratorTable(acc_table)
            wx.EVT_MENU(self, return_id, self.on_return)


            # respond to button click event
            self.button1.Bind(wx.EVT_BUTTON, self.button1Click, self.button1)

            # respond to button click event
            self.button2.Bind(wx.EVT_BUTTON, self.onCancel, self.button2)
                   

        else:
            if (len(line) <> 0):
                SO_utils.display_msg("Invalid or corrupted data file loaded in Edit ALI SOI dat file", "Edit ALI SOI data file")
            self.Destroy()

       
    def button1Click(self,event):
        """SAVE modified ALI SO DAT file button has been clicked"""

        try:
            # string of record to build
            lineout = []

            FOC = self.edit1.GetValue().ljust(1)
            NPA = self.edit2.GetValue().ljust(3) 
            TN = self.edit3.GetValue().ljust(7)
            HNum = self.edit4.GetValue().ljust(10)
            HNumSuffix = self.edit5.GetValue().ljust(4)
            
            PrDir = self.edit6.GetValue().ljust(2)
            streetname = self.edit7.GetValue().ljust(60)
            SSfx = self.edit8.GetValue().ljust(4)
            
            PoDir = self.edit9.GetValue().ljust(2)
            community = self.edit10.GetValue().ljust(32)
            ST = self.edit11.GetValue().ljust(2)
            
            location = self.edit12.GetValue().ljust(60)
            customername = self.edit13.GetValue().ljust(32)
            CLS = self.edit14.GetValue().ljust(1)
            TOS = self.edit15.GetValue().ljust(1)
            XCH = self.edit16.GetValue().ljust(4)
            
            ESN = self.edit17.GetValue().ljust(5)
            MNPA = self.edit18.GetValue().ljust(3)
            Main = self.edit19.GetValue().ljust(7)
            OrderNo = self.edit20.GetValue().ljust(10)
            
            ExDate = self.edit21.GetValue().ljust(6)
            COID = self.edit22.GetValue().ljust(4)
            CID1 = self.edit23.GetValue().ljust(5)
            
            SID = self.edit24.GetValue().ljust(1)
            ZIP = self.edit25.GetValue().ljust(5)
            
            ZIP4 = self.edit26.GetValue().ljust(4)
            general = self.edit27.GetValue().ljust(11)
            CCD = self.edit28.GetValue().ljust(3)
            
            comments = self.edit29.GetValue().ljust(30)
            XLON = self.edit30.GetValue().ljust(9)
            YLAT = self.edit31.GetValue().ljust(9)
            Zcoord = self.edit32.GetValue().ljust(5)
            
            CellID = self.edit33.GetValue().ljust(6)
            SecID = self.edit34.GetValue().ljust(1)
            TAR = self.edit35.GetValue().ljust(6)

            reserved1 = self.edit36.GetValue().ljust(21)
            ALT = self.edit37.GetValue().ljust(10)
            
            EEDate = self.edit38.GetValue().ljust(8)
            NENAreserved = self.edit39.GetValue().ljust(81)
            CID2 = self.edit40.GetValue().ljust(5)
            reserved2 = self.edit41.GetValue().ljust(31)
            EOR = self.edit42.GetValue().ljust(1)
                      

            # building the record
            lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
                   PoDir + community + ST + location + customername + CLS + TOS +   \
                   XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
                   SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
                   Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
                   NENAreserved + CID2 + reserved2 + EOR
            
            #print "lineout = [%s]" % lineout
            print len(lineout)

            if ((len(lineout) == ALI_REC_LENGTH) and (EOR == '*')):
                # Save edited file as
                SaveEditedDatFileNameAs(lineout)
                self.Destroy()
            else:
                print "Corrupted data record in Edit ALI SOI dat file"
                SO_utils.display_msg("Corrupted data record in Edit ALI SOI dat file", "Edit ALI SOI data file")
                self.Destroy()
            
        except:
            print "Exception Button1Click - Edit_ALI_SO_Dialog"
            self.Destroy()


    def onCancel(self, event):
        self.result = None
        self.Destroy()
        
    def on_return(self, event):
        """
        Enter to tab, move to next field
        """
        ctl = wx.Window_FindFocus()
        ctl.Navigate()




####################################################
def NetUseDeleteConnection_mapdrive():
    """
    Usage: Use "net use" to delete a mapped network drive
    """
    # map network drive using "net use" subprocess with Popen
    winCMD = 'net use   /delete  '+ mapdrive   
    cmdOutput = subprocess.Popen(winCMD, stdout=subprocess.PIPE, shell=True).communicate()


class ConnectRemoteDialog(wx.Dialog):
    """
    Class to define ConnectRemote dialog
    """
    def __init__(self):
        """Constructor"""
        wx.Dialog.__init__(self, None, title="Remote Connection", size=(360, 300))
        self.logged_in = False

        wx.StaticText(self, -1, "Location Directory's Host:", (15, 20))
        wx.StaticText(self, -1, "Host Log-in:", (15, 60))
        wx.StaticText(self, -1, "Password:", (15, 100))
        wx.StaticText(self, -1, "Provider's Location Path:", (15, 140))

        self.host = wx.TextCtrl(self, -1, '',  (160, 15), (150, -1))
        self.user = wx.TextCtrl(self, -1, '',  (160, 55), (150, -1))
        self.password = wx.TextCtrl(self, -1, '',  (160, 95), (150, -1), style=wx.TE_PASSWORD)
        self.parentpath = wx.TextCtrl(self, -1, '',  (160, 135), (150, -1))  

        self.remote = None

        con = wx.Button(self, 1, 'Connect', (70, 210))
        self.Bind(wx.EVT_BUTTON, self.OnConnect, id=1)

        can = wx.Button(self, 2, 'Cancel', (190, 210))
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=2)
            
    def OnConnect(self, event):            
        if not self.remote:
            host = self.host.GetValue()
            user = self.user.GetValue()
            password = self.password.GetValue()
            prov_parentpath = self.parentpath.GetValue()
                  
            try:                
                print "host = %s" % host
                print "user = %s" % user
                print "prov_parentpath = %s" % prov_parentpath
                                        
                if (VerifyRemoteCredential(host, user, password, prov_parentpath)):
                    print "You are now logged in!"                  
                    self.logged_in = True


                    self.Close()
                                     
                else:
                    print "Username or password is incorrect!"
                    SO_utils.display_msg("Username or password is incorrect!", "Remote Connection")
                    self.logged_in = False

            except AttributeError:
                self.remote = None

    def OnCancel(self, event):
            self.Close()


def VerifyRemoteCredential(host, user, password, parentpath):
        print host
        print user
        print parentpath
        
        try:            
            # map network drive using "net use" subprocess with Popen
            winCMD = 'net use   '+ mapdrive + '   \\\\' + host + '\\' + parentpath +  '  /user:' + user + '  ' + password    
            cmdOutput = subprocess.Popen(winCMD, stdout=subprocess.PIPE, shell=True).communicate()

            if (cmdOutput[0] == ""):
                print cmdOutput[0]
                # authentication failed
                return False
    
            elif (str.find(str(cmdOutput), 'The command completed successfully')):
                 print cmdOutput[0]
                 SO_utils.display_msg("Mapping network drive %s successfully" % mapdrive, "Connected")
                 return True
        except:
            print "Exception in VerifyRemoteCredential"
            return False


def SetMaxLength_ALI_fields(self):
    """
    Set Max Length for all ALI fields during editing single ALI record
    """
    # set max length for all fields in single ALI record
    self.edit1.SetMaxLength(1)
    self.edit2.SetMaxLength(3)
    self.edit3.SetMaxLength(7)
    self.edit4.SetMaxLength(10)
    self.edit5.SetMaxLength(4)
    self.edit6.SetMaxLength(2)
    self.edit7.SetMaxLength(60)
    self.edit8.SetMaxLength(4)
    self.edit9.SetMaxLength(2)
    self.edit10.SetMaxLength(32)
    self.edit11.SetMaxLength(2)
    self.edit12.SetMaxLength(60)
    self.edit13.SetMaxLength(32)
    self.edit14.SetMaxLength(1)
    self.edit15.SetMaxLength(1)
    self.edit16.SetMaxLength(4)
    self.edit17.SetMaxLength(5)
    self.edit18.SetMaxLength(3)
    self.edit19.SetMaxLength(7)
    self.edit20.SetMaxLength(10)
    self.edit21.SetMaxLength(6)
    self.edit22.SetMaxLength(4)
    self.edit23.SetMaxLength(5)
    self.edit24.SetMaxLength(1)
    self.edit25.SetMaxLength(5)
    self.edit26.SetMaxLength(4)
    self.edit27.SetMaxLength(11)
    self.edit28.SetMaxLength(3)
    self.edit29.SetMaxLength(30)
    self.edit30.SetMaxLength(9)
    self.edit31.SetMaxLength(9)
    self.edit32.SetMaxLength(5)
    self.edit33.SetMaxLength(6)
    self.edit34.SetMaxLength(1)
    self.edit35.SetMaxLength(6)
    self.edit36.SetMaxLength(21)
    self.edit37.SetMaxLength(10)
    self.edit38.SetMaxLength(8)
    self.edit39.SetMaxLength(81)
    self.edit40.SetMaxLength(5)
    self.edit41.SetMaxLength(31)
    self.edit42.SetMaxLength(1)


def Display_single_ALI_record_with_data(self,FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
                                            MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                 \
                                            SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR):
    """
    Display single ALI record with data
    """
    # required fields color = (166,244,244)

    wx.StaticText(self, -1, "FOC:", pos=wx.Point(15, 20))
    self.edit1 = wx.TextCtrl(self, -1, value=FOC, pos=wx.Point(15, 40), size=wx.Size(20, 20))
    self.edit1.SetMaxLength(1)
    prompt = "Required - Valid Function of Change: C, D, I, U,  M - column 1   (1)"
    self.edit1.SetToolTip(wx.ToolTip(prompt))
    self.edit1.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "NPA:", pos=wx.Point(55, 20))
    self.edit2 = wx.TextCtrl(self, -1, value=NPA, pos=wx.Point(55, 40), size=wx.Size(30, 20))
    self.edit2.SetMaxLength(3)
    prompt = "Required - Three-digit area code of the calling number  - column 2-4   (3)"
    self.edit2.SetToolTip(wx.ToolTip(prompt))
    self.edit2.SetBackgroundColour((166,244,244))  # suds yellow
        
    wx.StaticText(self, -1, "TN:", pos=wx.Point(95, 20))
    self.edit3 = wx.TextCtrl(self, -1, value=TN, pos=wx.Point(95, 40), size=wx.Size(60, 20))
    self.edit3.SetMaxLength(7)
    prompt = "Required - Seven-digit telephone number of the calling number  - column 5-11   (7)"
    self.edit3.SetToolTip(wx.ToolTip(prompt))        
    self.edit3.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "H No:", pos=wx.Point(165, 20))
    self.edit4 = wx.TextCtrl(self, -1, value=HNum, pos=wx.Point(165, 40), size=wx.Size(80, 20))
    self.edit4.SetMaxLength(10)
    prompt = "House Number  - column 12-21  (10)"
    self.edit4.SetToolTip(wx.ToolTip(prompt))        
    self.edit4.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "HN SFX:", pos=wx.Point(260, 20))
    self.edit5 = wx.TextCtrl(self, -1, value=HNumSuffix, pos=wx.Point(260, 40), size=wx.Size(35, 20))
    self.edit5.SetMaxLength(4)
    prompt = "House Number  Suffix - column 22-25   (4)"
    self.edit5.SetToolTip(wx.ToolTip(prompt))                
    self.edit5.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "PrDir:", pos=wx.Point(310, 20))
    self.edit6 = wx.TextCtrl(self, -1, value=PrDir, pos=wx.Point(310, 40), size=wx.Size(30, 20))
    self.edit6.SetMaxLength(2)
    prompt = "Prefix Directional  - column 26-27   (2)"
    self.edit6.SetToolTip(wx.ToolTip(prompt))       
    self.edit6.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Street Name:", pos=wx.Point(370, 20))
    self.edit7 = wx.TextCtrl(self, -1, value=streetname, pos=wx.Point(370, 40), size=wx.Size(365, 20))
    self.edit7.SetMaxLength(60)
    prompt = "Required - Street Name - GIS Based MSAG Street Name - column 28-87   (60)"
    self.edit7.SetToolTip(wx.ToolTip(prompt))               
    self.edit7.SetBackgroundColour((166,244,244))  # suds yellow
        

    wx.StaticText(self, -1, "SSfx:", pos=wx.Point(15, 80))
    self.edit8 = wx.TextCtrl(self, -1, value=SSfx, pos=wx.Point(15, 100), size=wx.Size(45, 20))
    self.edit8.SetMaxLength(4)
    prompt = "Street Suffix - column 88-91   (4)"
    self.edit8.SetToolTip(wx.ToolTip(prompt))          
    self.edit8.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "PoDir:", pos=wx.Point(65, 80))
    self.edit9 = wx.TextCtrl(self, -1, value=PoDir, pos=wx.Point(65, 100), size=wx.Size(30, 20))
    self.edit9.SetMaxLength(2)
    prompt = "Post Directional - column 92-93   (2)"
    self.edit9.SetToolTip(wx.ToolTip(prompt))                  
    self.edit9.SetBackgroundColour((255,255,197))  # suds yellow       

    wx.StaticText(self, -1, "Community Name:", pos=wx.Point(105, 80))
    self.edit10 = wx.TextCtrl(self, -1, value=community, pos=wx.Point(105, 100), size=wx.Size(220, 20))
    self.edit10.SetMaxLength(32)
    prompt = "Required - Community Name - column 94-125   (32)"
    self.edit10.SetToolTip(wx.ToolTip(prompt))                          
    self.edit10.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "ST:", pos=wx.Point(335, 80))
    self.edit11 = wx.TextCtrl(self, -1, value=ST, pos=wx.Point(335, 100), size=wx.Size(30, 20))
    self.edit11.SetMaxLength(2)
    prompt = "Required - State - column 126-127   (2)"
    self.edit11.SetToolTip(wx.ToolTip(prompt))                  
    self.edit11.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "Location:", pos=wx.Point(375, 80))
    self.edit12 = wx.TextCtrl(self, -1, value=location, pos=wx.Point(375, 100), size=wx.Size(360, 20))
    self.edit12.SetMaxLength(60)
    prompt = "Location - column 128-187  (60)"
    self.edit12.SetToolTip(wx.ToolTip(prompt))               
    self.edit12.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Customer Name:", pos=wx.Point(15, 140))
    self.edit13 = wx.TextCtrl(self, -1, value=customername, pos=wx.Point(15, 160), size=wx.Size(220, 20))
    self.edit13.SetMaxLength(32)
    prompt = "Required - Customer Name - column 188-219   (32)"
    self.edit13.SetToolTip(wx.ToolTip(prompt))                          
    self.edit13.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "CLS:", pos=wx.Point(250, 140))
    self.edit14 = wx.TextCtrl(self, -1, value=CLS, pos=wx.Point(250, 160), size=wx.Size(20, 20))
    self.edit14.SetMaxLength(1)
    prompt = "Required - Class of Services - valid values:  0 to 9  - column 220   (1)"
    self.edit14.SetToolTip(wx.ToolTip(prompt))
    self.edit14.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "TOS:", pos=wx.Point(285, 140))
    self.edit15 = wx.TextCtrl(self, -1, value=TOS, pos=wx.Point(285, 160), size=wx.Size(20, 20))
    self.edit15.SetMaxLength(1)
    prompt = "Required - Type of Services - valid values:  0 to 5  -  column 221   (1)"
    self.edit15.SetToolTip(wx.ToolTip(prompt))
    self.edit15.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "XCH:", pos=wx.Point(315, 140))
    self.edit16 = wx.TextCtrl(self, -1, value=XCH, pos=wx.Point(315, 160), size=wx.Size(40, 20))
    self.edit16.SetMaxLength(4)
    prompt = "Exchange - column 222-225     (4)"
    self.edit16.SetToolTip(wx.ToolTip(prompt))                
    self.edit16.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ESN:", pos=wx.Point(365, 140))
    self.edit17 = wx.TextCtrl(self, -1, value=ESN, pos=wx.Point(365, 160), size=wx.Size(50, 20))
    self.edit17.SetMaxLength(5)
    prompt = "Required - ESN - column 226-230     (5)"
    self.edit17.SetToolTip(wx.ToolTip(prompt))                
    self.edit17.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "MNPA:", pos=wx.Point(425, 140))
    self.edit18 = wx.TextCtrl(self, -1, value=MNPA, pos=wx.Point(425, 160), size=wx.Size(40, 20))
    self.edit18.SetMaxLength(3)
    prompt = "Main NPA - column 231-233     (3)"
    self.edit18.SetToolTip(wx.ToolTip(prompt))                
    self.edit18.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Main:", pos=wx.Point(475, 140))
    self.edit19 = wx.TextCtrl(self, -1, value=Main, pos=wx.Point(475, 160), size=wx.Size(60, 20))
    self.edit19.SetMaxLength(7)
    prompt = "Main Number - column 234-240     (7)"
    self.edit19.SetToolTip(wx.ToolTip(prompt))                
    self.edit19.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Order No:", pos=wx.Point(545, 140))
    self.edit20 = wx.TextCtrl(self, -1, value=OrderNo, pos=wx.Point(545, 160), size=wx.Size(80, 20))
    self.edit20.SetMaxLength(10)
    prompt = "Order Number - column 241-250     (10)"
    self.edit20.SetToolTip(wx.ToolTip(prompt))                
    self.edit20.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ExDate:", pos=wx.Point(635, 140))
    self.edit21 = wx.TextCtrl(self, -1, value=ExDate, pos=wx.Point(635, 160), size=wx.Size(60, 20))
    self.edit21.SetMaxLength(6)
    prompt = "Required - Extracted Date - MMDDYY - column 251-256     (6)"
    self.edit21.SetToolTip(wx.ToolTip(prompt))                
    self.edit21.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "COID:", pos=wx.Point(15, 200))
    self.edit22 = wx.TextCtrl(self, -1, value=COID, pos=wx.Point(15, 220), size=wx.Size(45, 20))
    self.edit22.SetMaxLength(4)
    prompt = "Required - County ID - column 257-260     (4)"
    self.edit22.SetToolTip(wx.ToolTip(prompt))                
    self.edit22.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "CID1:", pos=wx.Point(70, 200))
    self.edit23 = wx.TextCtrl(self, -1, value=CID1, pos=wx.Point(70, 220), size=wx.Size(50, 20))
    self.edit23.SetMaxLength(5)
    prompt = "Required - Company ID 1 - column 261-265   -  NENA registered Company Identification code of the Access Infrastructure  -  (5)"
    self.edit23.SetToolTip(wx.ToolTip(prompt))                
    self.edit23.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "SID:", pos=wx.Point(130, 200))
    self.edit24 = wx.TextCtrl(self, -1, value=SID, pos=wx.Point(130, 220), size=wx.Size(20, 20))
    self.edit24.SetMaxLength(1)
    prompt = "Required - Source ID - column 266     (1)"
    self.edit24.SetToolTip(wx.ToolTip(prompt))                
    self.edit24.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "ZIP:", pos=wx.Point(155, 200))
    self.edit25 = wx.TextCtrl(self, -1, value=ZIP, pos=wx.Point(155, 220), size=wx.Size(50, 20))
    self.edit25.SetMaxLength(5)
    prompt = "ZIP CODE   - column 267-271     (5)"
    self.edit25.SetToolTip(wx.ToolTip(prompt))                
    self.edit25.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ZIP4:", pos=wx.Point(220, 200))
    self.edit26 = wx.TextCtrl(self, -1, value=ZIP4, pos=wx.Point(220, 220), size=wx.Size(50, 20))
    self.edit26.SetMaxLength(4)
    prompt = "ZIP + 4   - column 272-275       (4)"
    self.edit26.SetToolTip(wx.ToolTip(prompt))                
    self.edit26.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "General:", pos=wx.Point(280, 200))
    self.edit27 = wx.TextCtrl(self, -1, value=general, pos=wx.Point(280, 220), size=wx.Size(90, 20))
    self.edit27.SetMaxLength(11)
    prompt = "General Use  - column 276-286        (11)"
    self.edit27.SetToolTip(wx.ToolTip(prompt))                
    self.edit27.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "CCD:", pos=wx.Point(380, 200))
    self.edit28 = wx.TextCtrl(self, -1, value=CCD, pos=wx.Point(380, 220), size=wx.Size(50, 20))
    self.edit28.SetMaxLength(3)
    prompt = "Customer Code   - column 287-289        (3)"
    self.edit28.SetToolTip(wx.ToolTip(prompt))                
    self.edit28.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Comments:", pos=wx.Point(450, 200))
    self.edit29 = wx.TextCtrl(self, -1, value=comments, pos=wx.Point(450, 220), size=wx.Size(210, 20))
    self.edit29.SetMaxLength(30)
    prompt = "Comments    - column 290-319        (30)"
    self.edit29.SetToolTip(wx.ToolTip(prompt))                
    self.edit29.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "XLON:", pos=wx.Point(15, 260))
    self.edit30 = wx.TextCtrl(self, -1, value=XLON, pos=wx.Point(15, 280), size=wx.Size(80, 20))
    self.edit30.SetMaxLength(9)
    prompt = "X Coordinate    -   Longgitude  - column 320-328        (9)"
    self.edit30.SetToolTip(wx.ToolTip(prompt))                
    self.edit30.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "YLAT:", pos=wx.Point(108, 260))
    self.edit31 = wx.TextCtrl(self, -1, value=YLAT, pos=wx.Point(108, 280), size=wx.Size(80, 20))
    self.edit31.SetMaxLength(9)
    prompt = "Y  Coordinate    -   Latitude   -  column 329-337        (9)"
    self.edit31.SetToolTip(wx.ToolTip(prompt))                
    self.edit31.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Zcoord:", pos=wx.Point(200, 260))
    self.edit32 = wx.TextCtrl(self, -1, value=Zcoord, pos=wx.Point(200, 280), size=wx.Size(50, 20))
    self.edit32.SetMaxLength(5)
    prompt = "Z  Coordinate    -   Structured Elevation  -  column 338-342        (5)"
    self.edit32.SetToolTip(wx.ToolTip(prompt))                
    self.edit32.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "CellID:", pos=wx.Point(260, 260))
    self.edit33 = wx.TextCtrl(self, -1, value=CellID, pos=wx.Point(260, 280), size=wx.Size(50, 20))
    self.edit33.SetMaxLength(6)
    prompt = "Cell ID  -  ID indicates a geographic region of cellular coverage  -  column 343-348        (6)"
    self.edit33.SetToolTip(wx.ToolTip(prompt))                
    self.edit33.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "SecID:", pos=wx.Point(320, 260))
    self.edit34 = wx.TextCtrl(self, -1, value=SecID, pos=wx.Point(320, 280), size=wx.Size(20, 20))
    self.edit34.SetMaxLength(1)
    prompt = "Sector ID  -  Subset/section of a cell  -  column 349        (1)"
    self.edit34.SetToolTip(wx.ToolTip(prompt))                
    self.edit34.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "TAR:", pos=wx.Point(360, 260))
    self.edit35 = wx.TextCtrl(self, -1, value=TAR, pos=wx.Point(360, 280), size=wx.Size(50, 20))
    self.edit35.SetMaxLength(6)
    prompt = "TAR Code   -  Taxing Area Rate Code  -  column 350-355        (6)"
    self.edit35.SetToolTip(wx.ToolTip(prompt))                
    self.edit35.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Reserved-1:", pos=wx.Point(420, 260))
    self.edit36 = wx.TextCtrl(self, -1, value=reserved1, pos=wx.Point(420, 280), size=wx.Size(180, 20))
    self.edit36.SetMaxLength(21)
    prompt = "Reserved for DBMS Provider's use  -  column 356-376       (21)"
    self.edit36.SetToolTip(wx.ToolTip(prompt))                
    self.edit36.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ALT:", pos=wx.Point(620, 260))
    self.edit37 = wx.TextCtrl(self, -1, value=ALT, pos=wx.Point(620, 280), size=wx.Size(80, 20))
    self.edit37.SetMaxLength(10)
    prompt = "Customer Number being remote call forwarded in Interim Number Portability service  -  column 377-386     (10)"
    self.edit37.SetToolTip(wx.ToolTip(prompt))                
    self.edit37.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "EEDate:", pos=wx.Point(15, 320))
    self.edit38 = wx.TextCtrl(self, -1, value=EEDate, pos=wx.Point(15, 340), size=wx.Size(60, 20))
    self.edit38.SetMaxLength(8)
    prompt = "Required - Expended Extract Date  -  YYYYMMDD  - column 387-394      (8)"
    self.edit38.SetToolTip(wx.ToolTip(prompt))                
    self.edit38.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "NENA Reserved:", pos=wx.Point(108, 320))
    self.edit39 = wx.TextCtrl(self, -1, value=NENAreserved, pos=wx.Point(108, 340), size=wx.Size(540, 20))
    self.edit39.SetMaxLength(81)
    prompt = "NENA Reserved - PSAP  Comment   -  column 395-475        (81)"
    self.edit39.SetToolTip(wx.ToolTip(prompt))                
    self.edit39.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "CID 2:", pos=wx.Point(670, 320))
    self.edit40 = wx.TextCtrl(self, -1, value=CID2, pos=wx.Point(670, 340), size=wx.Size(50, 20))
    self.edit40.SetMaxLength(5)
    prompt = "Data Provider ID (Company ID 2)   -  column 476-480        (5)"
    self.edit40.SetToolTip(wx.ToolTip(prompt))                
    self.edit40.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Reserved-2:", pos=wx.Point(15, 380))
    self.edit41 = wx.TextCtrl(self, -1, value=reserved2, pos=wx.Point(15, 400), size=wx.Size(220, 20))
    self.edit41.SetMaxLength(31)
    prompt = "Reserved for Database   -  column 481-511        (31)"
    self.edit41.SetToolTip(wx.ToolTip(prompt))                
    self.edit41.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "EOR:", pos=wx.Point(250, 380))
    self.edit42 = wx.TextCtrl(self, -1, value=EOR, pos=wx.Point(250, 400), size=wx.Size(20, 20))
    self.edit42.SetMaxLength(1)
    prompt = "Required - End of record   -  column  512        (1)"
    self.edit42.SetToolTip(wx.ToolTip(prompt))                
    self.edit42.SetBackgroundColour((166,244,244))  # suds yellow

    # get value out from text edit field, remove trailing spaces, then set value back to the edit field
    FOC = self.edit1.GetValue().strip()
    self.edit1.SetValue(FOC)

    NPA = self.edit2.GetValue().strip()
    self.edit2.SetValue(NPA)

    TN = self.edit3.GetValue().strip()
    self.edit3.SetValue(TN)

    HNum = self.edit4.GetValue().strip()
    self.edit4.SetValue(HNum)

    HNumSuffix = self.edit5.GetValue().strip()
    self.edit5.SetValue(HNumSuffix)

    PrDir = self.edit6.GetValue().strip()
    self.edit6.SetValue(PrDir)

    streetname = self.edit7.GetValue().strip()
    self.edit7.SetValue(streetname)

    SSfx = self.edit8.GetValue().strip()
    self.edit8.SetValue(SSfx)

    PoDir = self.edit9.GetValue().strip()
    self.edit9.SetValue(PoDir)

    community = self.edit10.GetValue().strip()
    self.edit10.SetValue(community)

    ST = self.edit11.GetValue().strip()
    self.edit11.SetValue(ST)

    location = self.edit12.GetValue().strip()
    self.edit12.SetValue(location)

    customername = self.edit13.GetValue().strip()
    self.edit13.SetValue(customername)

    CLS = self.edit14.GetValue().strip()
    self.edit14.SetValue(CLS)

    TOS = self.edit15.GetValue().strip()
    self.edit15.SetValue(TOS)

    XCH = self.edit16.GetValue().strip()
    self.edit16.SetValue(XCH)

    ESN = self.edit17.GetValue().strip()
    self.edit17.SetValue(ESN)

    MNPA = self.edit18.GetValue().strip()
    self.edit18.SetValue(MNPA)

    Main = self.edit19.GetValue().strip()
    self.edit19.SetValue(Main)

    OrderNo = self.edit20.GetValue().strip()
    self.edit20.SetValue(OrderNo)

    ExDate = self.edit21.GetValue().strip()
    self.edit21.SetValue(ExDate)

    COID = self.edit22.GetValue().strip()
    self.edit22.SetValue(COID)

    CID1 = self.edit23.GetValue().strip()
    self.edit23.SetValue(CID1)

    SID = self.edit24.GetValue().strip()
    self.edit24.SetValue(SID)

    ZIP = self.edit25.GetValue().strip()
    self.edit25.SetValue(ZIP)

    ZIP4 = self.edit26.GetValue().strip()
    self.edit26.SetValue(ZIP4)

    general = self.edit27.GetValue().strip()
    self.edit27.SetValue(general)

    CCD = self.edit28.GetValue().strip()
    self.edit28.SetValue(CCD)

    comments = self.edit29.GetValue().strip()
    self.edit29.SetValue(comments)

    XLON = self.edit30.GetValue().strip()
    self.edit30.SetValue(XLON)

    YLAT = self.edit31.GetValue().strip()
    self.edit31.SetValue(YLAT)

    Zcoord = self.edit32.GetValue().strip()
    self.edit32.SetValue(Zcoord)

    CellID = self.edit33.GetValue().strip()
    self.edit33.SetValue(CellID)

    SecID = self.edit34.GetValue().strip()
    self.edit34.SetValue(SecID)

    TAR = self.edit35.GetValue().strip()
    self.edit35.SetValue(TAR)

    reserved1 = self.edit36.GetValue().strip()
    self.edit36.SetValue(reserved1)

    ALT = self.edit37.GetValue().strip()
    self.edit37.SetValue(ALT)

    EEDate = self.edit38.GetValue().strip()
    self.edit38.SetValue(EEDate)

    NENAreserved = self.edit39.GetValue().strip()
    self.edit39.SetValue(NENAreserved)

    CID2 = self.edit40.GetValue().strip()
    self.edit40.SetValue(CID2)

    reserved2 = self.edit41.GetValue().strip()
    self.edit41.SetValue(reserved2)

    EOR = self.edit42.GetValue().strip()
    self.edit42.SetValue(EOR)


class Edit_ALI_SO_Dialog(wx.Dialog):

    def __init__(self, parent, id=-1, title="ALI SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(780, 580))        

        self.SetBackgroundColour((255,228,196))  # bisque
        
        # read data from ALI file
        retvars = Read_from_ALI_file()
        dline, reccount, selectedpath, selectedfile, currpath, elapsedtime = retvars

        self.list_ctrl = EditableListCtrl(self, size=(-1, 250), style=wx.LC_REPORT)
        #self.list_ctrl.SetBackgroundColour((166,244,244))  # cyan
        self.list_ctrl.SetBackgroundColour((217,255,219)) # vegaseat green
        
        # insert ALI columns to list ctrl
        insert_ALI_column_to_list_ctrl(self)

        # build self.myRowDict dictionary from dline dictionary
        index = 0
        #self.myRowDict = {}
        rcnt = 1        
        for key in sorted(dline):
            if dline.has_key(str(key)):                
                line = dline[str(key)]                
                #self.myRowDict[index] = line

                if ((reccount >= 1) and ((len(line) == (ALI_REC_LEN + 1)) or (len(line) == ALI_REC_LEN))):
                    # prepare more than one records
                    retvars = obtain_ALI_fields_from_line(line)
                    
                    FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,        \
                    MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                     \
                    SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR  =  retvars

                    insert_string_ALI_items_to_list_ctrl(self, index, FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,          \
                                                        community,ST,location,customername,CLS,TOS,XCH,ESN,MNPA,Main,OrderNo,          \
                                                        ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,    \
                                                        SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR)
                    
                else:
                    SO_utils.MsgBox("Invalid ALI SOI data file","Invalid Data")
                    self.result = None
                    self.Destroy()
                
                index += 1               
                rcnt += 1
                
            else:
                print 'NONE'

        #print self.myRowDict

        # self.label2 = status message
        self.label2 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label2.SetForegroundColour((50,30,236))       # 225,40,82 = red

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Total of  %d  record(s) loaded in  %f  seconds." % (reccount, elapsedtime))
        self.label3.Refresh()

        self.label4 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label4.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label4.SetLabel("Editing data file  %s   in   [%s]" % (selectedfile, selectedpath))
        self.label4.Refresh()
        
        self.saveBtn = wx.Button(self, wx.ID_ANY, "SAVE ALI records")
        self.saveBtn.Bind(wx.EVT_BUTTON, self.OnButtonClicked)
        self.saveBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        
        self.cancelBtn = wx.Button(self, wx.ID_ANY, "Cancel")
        self.cancelBtn.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.cancelBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        
        # Create some sizers
        mainSizer = wx.BoxSizer(wx.VERTICAL)        
        mainSizer.Add(self.list_ctrl, 1, wx.ALL|wx.EXPAND, 5)
        mainSizer.Add(self.label2, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label3, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label4, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.saveBtn, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.cancelBtn, 0, wx.ALL|wx.CENTER, 5)        
        self.SetSizer(mainSizer)
        

    def OnButtonClicked(self, e):
        """
        loop through all the rows,  item.GetText() for all columns on each row
        """
        count = self.list_ctrl.GetItemCount()

        self.saveBtn.Disable()

        start = time.time()                               # start the stopwatch
        print "start timing:  %f" % start        
        time.clock()

        for row in range(count):            
            # get values of every columns in current row
            lineout = GetText_from_ALI_columns_currRow(self, row)

            print len(lineout)
            print "\nlineout = [%s]\n" % lineout

            try:
                # write current record to temp ALI SOI data file
                with open(ALIpath,"a") as A_datfile:
                    A_datfile.write(str(lineout) + '\n')
                    self.label2.SetLabel("Processing ......... %d   of  %d" % (row, count))
                    self.label2.Refresh()

            except:
                print "Exception in writing ALI record to  %s\n" % A_datfile

        elapsedtime = time.time() - start                  # end timing
        print "end timing:  %f" % elapsedtime

        self.label2.SetLabel("Elapsed time = %f+  seconds" % elapsedtime)
        self.label2.Refresh()

        SO_utils.MsgBox("%s  records were added to file\n   %s    in   %s   seconds" % (count,A_datfile, elapsedtime),"Current records were added to file")
        self.Destroy()  

    def OnCancel(self, e):
        self.result = None
        self.Destroy()


#######################################
class ALI(object):
    def __init__(self, FOC, NPA, TN, HNum, HNumSuffix, PrDir, streetname,                          \
                       SSfx, PoDir, community, ST, location, customername, CLS, TOS, XCH, ESN,     \
                       MNPA, Main, OrderNo, ExDate, COID, CID1, SID, ZIP, ZIP4,                    \
                       general, CCD, comments, XLON, YLAT, Zcoord, CellID,                         \
                       SecID, TAR, reserved1, ALT, EEDate, NENAreserved, CID2,                     \
                       reserved2, EOR):
        
        self.FOC = FOC
        self.NPA = NPA
        self.TN = TN
        self.HNum = HNum
        self.HNumSuffix = HNumSuffix
        self.PrDir = PrDir
        self.streetname = streetname
        self.SSfx = SSfx
        self.PoDir = PoDir
        self.community = community
        self.ST = ST
        self.location = location
        self.customername = customername
        self.CLS = CLS
        self.TOS = TOS
        self.XCH = XCH
        self.ESN = ESN
        self.MNPA = MNPA
        self.Main = Main
        self.OrderNo = OrderNo
        self.ExDate = ExDate
        self.COID = COID
        self.CID1 = CID1
        self.SID = SID
        self.ZIP = ZIP
        self.ZIP4 = ZIP4
        self.general = general
        self.CCD = CCD
        self.comments = comments
        self.XLON = XLON
        self.YLAT = YLAT
        self.Zcoord = Zcoord
        self.CellID = CellID
        self.SecID = SecID
        self.TAR = TAR
        self.reserved1 = reserved1
        self.ALT = ALT
        self.EEDate = EEDate
        self.NENAreserved = NENAreserved
        self.CID2 = CID2
        self.reserved2 = reserved2
        self.EOR = EOR



#######################################
class Edit_ALI_SO_Dialog_OLV(wx.Dialog):

    def __init__(self, parent, id=-1, title="ALI SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(780, 580))        
        self.SetBackgroundColour((255,228,196))  # bisque

        # read data from ALI file
        retvars = Read_from_ALI_file_OLV()
        line, dline, reccount, selectedpath, selectedfile, currpath, elapsedtime = retvars

        # obtain ALI fields from line
        retvars = obtain_ALI_fields_from_line(line)
               
        FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,    \
        MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                 \
        SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR  =  retvars
        
        self.dataOlv = ObjectListView(self, wx.ID_ANY, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
        self.dataOlv.SetBackgroundColour((217,255,219)) # vegaseat green

        self.dataOlv.Bind(wx.EVT_MOTION, self.updateTooltip)
        self.dataOlv.Bind(wx.EVT_MOTION, self.OnMouseMotion)

        # Allow the cell values to be edited when double-clicked
        self.dataOlv.cellEditMode = ObjectListView.CELLEDIT_SINGLECLICK
        set_ALI_columns(self)

        index = 0
        rcnt = 1        
        for key in sorted(dline):
            if dline.has_key(str(key)):                
                line = dline[str(key)]                

                #print "line = [%s]\n" % line
                #print len(line)

                if ((reccount >= 1) and ((len(line) == (ALI_REC_LEN + 1) or (len(line) == ALI_REC_LEN)))):
                    # prepare more than one records
                    retvars = obtain_ALI_fields_from_line(line)
        
                    FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,    \
                    MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                 \
                    SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR  =  retvars

                    self.ALIrecord = [ALI(FOC, NPA, TN, HNum, HNumSuffix, PrDir, streetname,                        \
                                          SSfx, PoDir, community, ST, location, customername, CLS, TOS, XCH, ESN,   \
                                          MNPA, Main, OrderNo, ExDate, COID, CID1, SID, ZIP, ZIP4,                  \
                                          general, CCD, comments, XLON, YLAT, Zcoord, CellID,                       \
                                          SecID, TAR, reserved1, ALT, EEDate, NENAreserved, CID2, reserved2, EOR)]


                    self.dataOlv.AddObjects(self.ALIrecord)
                                      
                else:
                    SO_utils.MsgBox("Invalid ALI SOI data file","Invalid Data")
                    self.result = None
                    self.Destroy()
                    
                index += 1               
                rcnt += 1
                
            else:
                print 'NONE'
                        
        #print self.myRowDict

        # self.label2 = status message
        self.label2 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label2.SetForegroundColour((50,30,236))       # 225,40,82 = red

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Total of  %d  record(s) loaded in  %f  seconds." % (reccount, elapsedtime))
        self.label3.Refresh()

        self.label4 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label4.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label4.SetLabel("Editing data file  %s   in   [%s]" % (selectedfile, selectedpath))
        self.label4.Refresh()
        
        self.saveBtn = wx.Button(self, wx.ID_ANY, "SAVE current items on the list to data file")
        self.saveBtn.SetToolTipString("SAVE current items on the list to data file")
        self.saveBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        self.saveBtn.Bind(wx.EVT_BUTTON, self.OnButtonClicked)

        self.deleteBtn = wx.Button(self, wx.ID_ANY, "Remove items from list")
        self.deleteBtn.SetToolTipString("Check to select one or many item(s) on the list, then click 'Remove items from list' ")
        self.deleteBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.OnDelete)

        self.cancelBtn = wx.Button(self, wx.ID_ANY, "Cancel")
        self.cancelBtn.SetToolTipString("Discard changes of current items on the list")
        self.cancelBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        self.cancelBtn.Bind(wx.EVT_BUTTON, self.OnCancel)
        
        # Create some sizers
        mainSizer = wx.BoxSizer(wx.VERTICAL)        
        mainSizer.Add(self.dataOlv, 1, wx.ALL|wx.EXPAND, 5)
        mainSizer.Add(self.label2, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label3, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label4, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.saveBtn, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.deleteBtn, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.cancelBtn, 0, wx.ALL|wx.CENTER, 5)
               
        self.SetSizer(mainSizer)
        

    def OnButtonClicked(self, e):
        """
        loop through all the rows,  item.GetText() for all columns on each row
        """
        count = self.dataOlv.GetItemCount()

        self.saveBtn.Disable()

        """ Save edited records to file """        
        # Save away the edited text        
        dlg = wx.FileDialog(
                    None, message="Save file as ...",
                    defaultDir=".",
                    defaultFile="", wildcard="*.dat", style=wx.SAVE
                    )
        if dlg.ShowModal() == wx.ID_OK:      
                # Open the file for write, write, close
                filename = dlg.GetFilename()
                dirname = dlg.GetDirectory()
                filehandle = open(os.path.join(dirname, filename),'w')
        # Get rid of the dialog to keep things tidy
        dlg.Destroy()

        start = time.time()                               # start the stopwatch
        print "start timing:  %f" % start        
        time.clock()

        for row in range(count):            
            # get values of every columns in current row
            retvar = GetText_from_ALI_columns_currRow_OLV_3(self, row)
            lineout = retvar

            #print len(lineout)
            #print "\nlineout = [%s]\n" % lineout

            try:
                ## write current record to temp ALI SOI data file
                #with open(ALIpath,"a") as A_datfile:
                #    A_datfile.write(str(lineout) + '\n')
                #    self.label2.SetLabel("Processing ......... %d   of  %d" % (row, count))
                #    self.label2.Refresh()

                filehandle.write(str(lineout) + '\n')
                self.label2.SetLabel("Processing ......... %d   of  %d" % (row, count))
                self.label2.Refresh()
            except:
                print "Exception in writing ALI record to  %s\n" % filename

        filehandle.close()

        elapsedtime = time.time() - start                  # end timing
        print "end timing:  %f" % elapsedtime

        self.label2.SetLabel("Elapsed time = %f+  seconds" % elapsedtime)
        self.label2.Refresh()
        SO_utils.MsgBox("%s  records were added to file\n   %s    in   %s   seconds" % (count,filename, elapsedtime),"Current records were added to file")
        self.Destroy()  


    def OnCancel(self, e):
        self.result = None
        self.Destroy()


    def OnDelete(self, e):
        objects = self.dataOlv.GetObjects()
        
        for obj in objects:
            if (self.dataOlv.GetCheckState(obj)):
                 print "\nRemove TN = %s - House Number = %s - Street name = %s  from the list." % (obj.TN, obj.HNum, obj.streetname)
                 self.dataOlv.RemoveObject(obj)
            
        self.dataOlv.RefreshObjects(objects)        
        e.Skip()


    def OnMouseMotion(self, evt):
        """
            self.lc = wx.ListCtrl(self, style=wx.LC_REPORT)
            self.lc.Bind(wx.EVT_MOTION, self.OnMouseMotion)

        """
        pos = self.dataOlv.ScreenToClient(wx.GetMousePosition())
        item_index, flag = self.dataOlv.HitTest(pos)
        tip = self.dataOlv.GetToolTip()

        #if flag == wx.LIST_HITTEST_ONITEMLABEL:
        #    tip.SetToolTipString('Some information about ' + self.dataOlv.GetItemText(item_index))
        #else:
        #    tip.SetToolTipString('')
        #print flag

        #if item_index != -1:
        #    msg = "%s is a good book!" % self.dataOlv.GetItemText(item_index)
        #    self.dataOlv.SetToolTipString(msg)
        #else:
        #    self.dataOlv.SetToolTipString("")

        evt.Skip()


    def updateTooltip(self, event):
        """
        Update the tooltip!
        """
        pos = wx.GetMousePosition()
        mouse_pos = self.dataOlv.ScreenToClient(pos)
        item_index, flag = self.dataOlv.HitTest(mouse_pos)

        #print flag
        #if item_index != -1:
        #    msg = "%s = %s\n" % (self.dataOlv.GetItemText(item_index), flag)
        #    self.dataOlv.SetToolTipString(msg)
        #else:
        #    self.dataOlv.SetToolTipString("")
        
        #item.author = "This is me"
        #item = self.dataOlv.GetSelectedObject()
        #tip = "%s is the field" % item.author
        #event.GetEventObject().SetToolTipString(tip)

        event.Skip()



def Load_ALI_SO_File():
    """
    Load ALI SO dat file (length 512)
    """
    try:
       line = []
       
       #selected_ALI_datfilename = Select_ALI_dat_file()
       #currpath = os.getcwd()

       prefixed = ''
       extension_list = ['dat', 'DAT']
       selected_ALI_datfilename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
       selectedpath, selectedfile = selected_ALI_datfilename

       currpath = selectedpath + "\\" + selectedfile
       
       if (os.path.exists(currpath)):
           dfile = open(currpath, 'r')
           line = dfile.read(ALI_REC_LENGTH)
   
       if (len(line) <> ALI_REC_LENGTH):
           print "Corrupted data record in Load ALI SOI file"

       return line, selectedpath, selectedfile 
       dfile.close()
       
    except:
       print "Exception loading ALI SO dat file"
       return line, selectedpath, selectedfile
 
         
def Select_ALI_dat_file():
    extension_list = ['dat','DAT']
    prefixed = ''
    listDATfilenames_w_extension = SO_utils.get_filenames_filter_startswith_and_extensions(prefixed, extension_list)
    selectedfilename =""
    datdlg = wx.SingleChoiceDialog( None,
                                    "Select a DAT file",
                                    "Listing of available DAT files", listDATfilenames_w_extension, wx.CHOICEDLG_STYLE)
    if (datdlg.ShowModal() == wx.ID_OK):
        selectedfilename = datdlg.GetStringSelection()                

    datdlg.Destroy()
    return selectedfilename       


def SaveEditedDatFileNameAs(lineout):    
    """ Save edited file """
    try:
        # Save away the edited text        
        dlg = wx.FileDialog(
                    None, message="Save file as ...",
                    defaultDir=".",
                    defaultFile="", wildcard="*.dat", style=wx.SAVE
                    )

        if dlg.ShowModal() == wx.ID_OK:       

                # Open the file for write, write, close
                filename = dlg.GetFilename()
                dirname = dlg.GetDirectory()

                filehandle = open(os.path.join(dirname, filename),'w')

                filehandle.write(lineout)
                filehandle.close()

        # Get rid of the dialog to keep things tidy
        dlg.Destroy()
    except:
        print "Exception in SaveEditedDatFileNameAs"



def Refresh_ALI_self_edit(self):
    """
    refresh all self.edit... of single ALI DAT record 42 fields
    """
    self.edit1.Value = ''
    self.edit1.Refresh()

    self.edit2.Value = ''
    self.edit2.Refresh()

    self.edit3.Value = ''
    self.edit3.Refresh()

    self.edit4.Value = ''
    self.edit4.Refresh()

    self.edit5.Value = ''
    self.edit5.Refresh()

    self.edit6.Value = ''
    self.edit6.Refresh()

    self.edit7.Value = ''
    self.edit7.Refresh()

    self.edit8.Value = ''
    self.edit8.Refresh()

    self.edit9.Value = ''
    self.edit9.Refresh()

    self.edit10.Value = ''
    self.edit10.Refresh()

    self.edit11.Value = ''
    self.edit11.Refresh()

    self.edit12.Value = ''
    self.edit12.Refresh()

    self.edit13.Value = ''
    self.edit13.Refresh()

    self.edit14.Value = ''
    self.edit14.Refresh()

    self.edit15.Value = ''
    self.edit15.Refresh()

    self.edit16.Value = ''
    self.edit16.Refresh()

    self.edit17.Value = ''
    self.edit17.Refresh()

    self.edit18.Value = ''
    self.edit18.Refresh()

    self.edit19.Value = ''
    self.edit19.Refresh()

    self.edit20.Value = ''
    self.edit20.Refresh()

    self.edit21.Value = ''
    self.edit21.Refresh()

    self.edit22.Value = ''
    self.edit22.Refresh()

    self.edit23.Value = ''
    self.edit23.Refresh()

    self.edit24.Value = ''
    self.edit24.Refresh()

    self.edit25.Value = ''
    self.edit25.Refresh()

    self.edit26.Value = ''
    self.edit26.Refresh()

    self.edit27.Value = ''
    self.edit27.Refresh()

    self.edit28.Value = ''
    self.edit28.Refresh()

    self.edit29.Value = ''
    self.edit29.Refresh()

    self.edit30.Value = ''
    self.edit30.Refresh()

    self.edit31.Value = ''
    self.edit31.Refresh()

    self.edit32.Value = ''
    self.edit32.Refresh()

    self.edit33.Value = ''
    self.edit33.Refresh()

    self.edit34.Value = ''
    self.edit34.Refresh()

    self.edit35.Value = ''
    self.edit35.Refresh()

    self.edit36.Value = ''
    self.edit36.Refresh()

    self.edit37.Value = ''
    self.edit37.Refresh()

    self.edit38.Value = ''
    self.edit38.Refresh()

    self.edit39.Value = ''
    self.edit39.Refresh()

    self.edit40.Value = ''
    self.edit40.Refresh()

    self.edit41.Value = ''
    self.edit41.Refresh()

    self.edit42.Value = '*'
    self.edit42.Refresh()



def Display_Single_ALI_record(self):
    """
    display single ALI record fields
    """
    wx.StaticText(self, -1, "FOC:", pos=wx.Point(15, 20))
    self.edit1 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 40), size=wx.Size(20, 20))
    self.edit1.SetMaxLength(1)
    prompt = "Required - Valid Function of Change: C, D, I, U,  M - column 1   (1)"
    self.edit1.SetToolTip(wx.ToolTip(prompt))
    self.edit1.SetBackgroundColour((166,244,244))  # cyan

    wx.StaticText(self, -1, "NPA:", pos=wx.Point(55, 20))
    self.edit2 = wx.TextCtrl(self, -1, value='', pos=wx.Point(55, 40), size=wx.Size(30, 20))
    self.edit2.SetMaxLength(3)
    prompt = "Required - Three-digit area code of the calling number  - column 2-4   (3)"
    self.edit2.SetToolTip(wx.ToolTip(prompt))
    self.edit2.SetBackgroundColour((166,244,244))  # cyan
        
    wx.StaticText(self, -1, "TN:", pos=wx.Point(95, 20))
    self.edit3 = wx.TextCtrl(self, -1, value='', pos=wx.Point(95, 40), size=wx.Size(60, 20))
    self.edit3.SetMaxLength(7)
    prompt = "Required - Seven-digit telephone number of the calling number  - column 5-11   (7)"
    self.edit3.SetToolTip(wx.ToolTip(prompt))        
    self.edit3.SetBackgroundColour((166,244,244))  # cyan

    wx.StaticText(self, -1, "House Number:", pos=wx.Point(165, 20))
    self.edit4 = wx.TextCtrl(self, -1, value='', pos=wx.Point(165, 40), size=wx.Size(80, 20))
    self.edit4.SetMaxLength(10)
    prompt = "House Number  - column 12-21  (10)"
    self.edit4.SetToolTip(wx.ToolTip(prompt))        
    self.edit4.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "HN SFX:", pos=wx.Point(260, 20))
    self.edit5 = wx.TextCtrl(self, -1, value='', pos=wx.Point(260, 40), size=wx.Size(35, 20))
    self.edit5.SetMaxLength(4)
    prompt = "House Number  Suffix - column 22-25   (4)"
    self.edit5.SetToolTip(wx.ToolTip(prompt))                
    self.edit5.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "PrDir:", pos=wx.Point(310, 20))
    self.edit6 = wx.TextCtrl(self, -1, value='', pos=wx.Point(310, 40), size=wx.Size(30, 20))
    self.edit6.SetMaxLength(2)
    prompt = "Prefix Directional  - column 26-27   (2)"
    self.edit6.SetToolTip(wx.ToolTip(prompt))       
    self.edit6.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Street Name:", pos=wx.Point(370, 20))
    self.edit7 = wx.TextCtrl(self, -1, value='', pos=wx.Point(370, 40), size=wx.Size(365, 20))
    self.edit7.SetMaxLength(60)
    prompt = "Required - Street Name - GIS Based MSAG Street Name - column 28-87   (60)"
    self.edit7.SetToolTip(wx.ToolTip(prompt))               
    self.edit7.SetBackgroundColour((166,244,244))  # cyan
        

    wx.StaticText(self, -1, "SSfx:", pos=wx.Point(15, 80))
    self.edit8 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 100), size=wx.Size(45, 20))
    self.edit8.SetMaxLength(4)
    prompt = "Street Suffix - column 88-91   (4)"
    self.edit8.SetToolTip(wx.ToolTip(prompt))          
    self.edit8.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "PoDir:", pos=wx.Point(65, 80))
    self.edit9 = wx.TextCtrl(self, -1, value='', pos=wx.Point(65, 100), size=wx.Size(30, 20))
    self.edit9.SetMaxLength(2)
    prompt = "Post Directional - column 92-93   (2)"
    self.edit9.SetToolTip(wx.ToolTip(prompt))                  
    self.edit9.SetBackgroundColour((255,255,197))  # suds yellow       

    wx.StaticText(self, -1, "Community Name:", pos=wx.Point(105, 80))
    self.edit10 = wx.TextCtrl(self, -1, value='', pos=wx.Point(105, 100), size=wx.Size(220, 20))
    self.edit10.SetMaxLength(32)
    prompt = "Required - Community Name - column 94-125   (32)"
    self.edit10.SetToolTip(wx.ToolTip(prompt))                          
    self.edit10.SetBackgroundColour((166,244,244))  # cyan

    wx.StaticText(self, -1, "ST:", pos=wx.Point(335, 80))
    self.edit11 = wx.TextCtrl(self, -1, value='', pos=wx.Point(335, 100), size=wx.Size(30, 20))
    self.edit11.SetMaxLength(2)
    prompt = "Required - State - column 126-127   (2)"
    self.edit11.SetToolTip(wx.ToolTip(prompt))                  
    self.edit11.SetBackgroundColour((166,244,244))  # cyan

    wx.StaticText(self, -1, "Location:", pos=wx.Point(375, 80))
    self.edit12 = wx.TextCtrl(self, -1, value='', pos=wx.Point(375, 100), size=wx.Size(360, 20))
    self.edit12.SetMaxLength(60)
    prompt = "Location - column 128-187  (60)"
    self.edit12.SetToolTip(wx.ToolTip(prompt))               
    self.edit12.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Customer Name:", pos=wx.Point(15, 140))
    self.edit13 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 160), size=wx.Size(220, 20))
    self.edit13.SetMaxLength(32)
    prompt = "Required - Customer Name - column 188-219   (32)"
    self.edit13.SetToolTip(wx.ToolTip(prompt))                          
    self.edit13.SetBackgroundColour((166,244,244))  # cyan

    wx.StaticText(self, -1, "CLS:", pos=wx.Point(250, 140))
    self.edit14 = wx.TextCtrl(self, -1, value='', pos=wx.Point(250, 160), size=wx.Size(20, 20))
    self.edit14.SetMaxLength(1)
    prompt = "Required - Class of Services  -  column 220   (1)"
    self.edit14.SetToolTip(wx.ToolTip(prompt))
    self.edit14.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "TOS:", pos=wx.Point(285, 140))
    self.edit15 = wx.TextCtrl(self, -1, value='', pos=wx.Point(285, 160), size=wx.Size(20, 20))
    self.edit15.SetMaxLength(1)
    prompt = "Required - Type of Services - valid values: 0 to 6  - column 221   (1)"
    self.edit15.SetToolTip(wx.ToolTip(prompt))
    self.edit15.SetBackgroundColour((166,244,244))  # cyan

    wx.StaticText(self, -1, "XCH:", pos=wx.Point(315, 140))
    self.edit16 = wx.TextCtrl(self, -1, value='', pos=wx.Point(315, 160), size=wx.Size(40, 20))
    self.edit16.SetMaxLength(4)
    prompt = "Exchange - column 222-225     (4)"
    self.edit16.SetToolTip(wx.ToolTip(prompt))                
    self.edit16.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ESN:", pos=wx.Point(365, 140))
    self.edit17 = wx.TextCtrl(self, -1, value='', pos=wx.Point(365, 160), size=wx.Size(50, 20))
    self.edit17.SetMaxLength(5)
    prompt = "Required - ESN - column 226-230     (5)"
    self.edit17.SetToolTip(wx.ToolTip(prompt))                
    self.edit17.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "MNPA:", pos=wx.Point(425, 140))
    self.edit18 = wx.TextCtrl(self, -1, value='', pos=wx.Point(425, 160), size=wx.Size(40, 20))
    self.edit18.SetMaxLength(3)
    prompt = "Main NPA - column 231-233     (3)"
    self.edit18.SetToolTip(wx.ToolTip(prompt))                
    self.edit18.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Main Number:", pos=wx.Point(475, 140))
    self.edit19 = wx.TextCtrl(self, -1, value='', pos=wx.Point(475, 160), size=wx.Size(60, 20))
    self.edit19.SetMaxLength(7)
    prompt = "Main Number - column 234-240     (7)"
    self.edit19.SetToolTip(wx.ToolTip(prompt))                
    self.edit19.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Order No", pos=wx.Point(545, 140))
    self.edit20 = wx.TextCtrl(self, -1, value='', pos=wx.Point(545, 160), size=wx.Size(80, 20))
    self.edit20.SetMaxLength(10)
    prompt = "Order Number - column 241-250     (10)"
    self.edit20.SetToolTip(wx.ToolTip(prompt))                
    self.edit20.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ExtDate", pos=wx.Point(635, 140))
    self.edit21 = wx.TextCtrl(self, -1, value='', pos=wx.Point(635, 160), size=wx.Size(60, 20))
    self.edit21.SetMaxLength(6)
    prompt = "Required - Extracted Date - MMDDYY - column 251-256     (6)"
    self.edit21.SetToolTip(wx.ToolTip(prompt))                
    self.edit21.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "COID", pos=wx.Point(15, 200))
    self.edit22 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 220), size=wx.Size(45, 20))
    self.edit22.SetMaxLength(4)
    prompt = "Required - County ID - column 257-260     (4)"
    self.edit22.SetToolTip(wx.ToolTip(prompt))                
    self.edit22.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "CID1", pos=wx.Point(70, 200))
    self.edit23 = wx.TextCtrl(self, -1, value='', pos=wx.Point(70, 220), size=wx.Size(50, 20))
    self.edit23.SetMaxLength(5)
    prompt = "Required - Company ID 1 - column 261-265   - NENA registered Company Identification code of the Access Infrastructure  -  (5)"
    self.edit23.SetToolTip(wx.ToolTip(prompt))                
    self.edit23.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "SID", pos=wx.Point(130, 200))
    self.edit24 = wx.TextCtrl(self, -1, value='', pos=wx.Point(130, 220), size=wx.Size(20, 20))
    self.edit24.SetMaxLength(1)
    prompt = "Required - Source ID - Daily = Space, Initial Load = C   -  column 266     (1)"
    self.edit24.SetToolTip(wx.ToolTip(prompt))                
    self.edit24.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "ZIP", pos=wx.Point(155, 200))
    self.edit25 = wx.TextCtrl(self, -1, value='', pos=wx.Point(155, 220), size=wx.Size(50, 20))
    self.edit25.SetMaxLength(5)
    prompt = "ZIP CODE   - column 267-271     (5)"
    self.edit25.SetToolTip(wx.ToolTip(prompt))                
    self.edit25.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ZIP4", pos=wx.Point(220, 200))
    self.edit26 = wx.TextCtrl(self, -1, value='', pos=wx.Point(220, 220), size=wx.Size(50, 20))
    self.edit26.SetMaxLength(4)
    prompt = "ZIP + 4   - column 272-275       (4)"
    self.edit26.SetToolTip(wx.ToolTip(prompt))                
    self.edit26.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "General Use", pos=wx.Point(280, 200))
    self.edit27 = wx.TextCtrl(self, -1, value='', pos=wx.Point(280, 220), size=wx.Size(90, 20))
    self.edit27.SetMaxLength(11)
    prompt = "General Use  - column 276-286        (11)"
    self.edit27.SetToolTip(wx.ToolTip(prompt))                
    self.edit27.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "CCD", pos=wx.Point(380, 200))
    self.edit28 = wx.TextCtrl(self, -1, value='', pos=wx.Point(380, 220), size=wx.Size(50, 20))
    self.edit28.SetMaxLength(3)
    prompt = "Customer Code   - column 287-289        (3)"
    self.edit28.SetToolTip(wx.ToolTip(prompt))                
    self.edit28.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Comments", pos=wx.Point(450, 200))
    self.edit29 = wx.TextCtrl(self, -1, value='', pos=wx.Point(450, 220), size=wx.Size(210, 20))
    self.edit29.SetMaxLength(30)
    prompt = "Comments    - column 290-319        (30)"
    self.edit29.SetToolTip(wx.ToolTip(prompt))                
    self.edit29.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "X Coord", pos=wx.Point(15, 260))
    self.edit30 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 280), size=wx.Size(80, 20))
    self.edit30.SetMaxLength(9)
    prompt = "X Coordinate    -   Longitude  - column 320-328        (9)"
    self.edit30.SetToolTip(wx.ToolTip(prompt))                
    self.edit30.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Y Coord", pos=wx.Point(108, 260))
    self.edit31 = wx.TextCtrl(self, -1, value='', pos=wx.Point(108, 280), size=wx.Size(80, 20))
    self.edit31.SetMaxLength(9)
    prompt = "Y  Coordinate    -   Latitude   -  column 329-337        (9)"
    self.edit31.SetToolTip(wx.ToolTip(prompt))                
    self.edit31.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Z Coord", pos=wx.Point(200, 260))
    self.edit32 = wx.TextCtrl(self, -1, value='', pos=wx.Point(200, 280), size=wx.Size(50, 20))
    self.edit32.SetMaxLength(5)
    prompt = "Z  Coordinate    -   Structured Elevation  -  column 338-342        (5)"
    self.edit32.SetToolTip(wx.ToolTip(prompt))                
    self.edit32.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Cell ID", pos=wx.Point(260, 260))
    self.edit33 = wx.TextCtrl(self, -1, value='', pos=wx.Point(260, 280), size=wx.Size(50, 20))
    self.edit33.SetMaxLength(6)
    prompt = "Cell ID  -  ID indicates a geographic region of cellular coverage  -  column 343-348        (6)"
    self.edit33.SetToolTip(wx.ToolTip(prompt))                
    self.edit33.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "SecID", pos=wx.Point(320, 260))
    self.edit34 = wx.TextCtrl(self, -1, value='', pos=wx.Point(320, 280), size=wx.Size(20, 20))
    self.edit34.SetMaxLength(1)
    prompt = "Sector ID  -  Subset/section of a cell  -  column 349        (1)"
    self.edit34.SetToolTip(wx.ToolTip(prompt))                
    self.edit34.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "TAR", pos=wx.Point(360, 260))
    self.edit35 = wx.TextCtrl(self, -1, value='', pos=wx.Point(360, 280), size=wx.Size(50, 20))
    self.edit35.SetMaxLength(6)
    prompt = "TAR Code   -  Taxing Area Rate Code  -  column 350-355        (6)"
    self.edit35.SetToolTip(wx.ToolTip(prompt))                
    self.edit35.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Reserved-1", pos=wx.Point(420, 260))
    self.edit36 = wx.TextCtrl(self, -1, value='', pos=wx.Point(420, 280), size=wx.Size(180, 20))
    self.edit36.SetMaxLength(21)
    prompt = "Reserved for DBMS Provider's use  -  column 356-376       (21)"
    self.edit36.SetToolTip(wx.ToolTip(prompt))                
    self.edit36.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ALT", pos=wx.Point(620, 260))
    self.edit37 = wx.TextCtrl(self, -1, value='', pos=wx.Point(620, 280), size=wx.Size(80, 20))
    self.edit37.SetMaxLength(10)
    prompt = "Customer Number being remote call forwarded in Interim Number Portability service  -  column 377-386     (10)"
    self.edit37.SetToolTip(wx.ToolTip(prompt))                
    self.edit37.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "ExpExtDate", pos=wx.Point(15, 320))
    self.edit38 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 340), size=wx.Size(60, 20))
    self.edit38.SetMaxLength(8)
    prompt = "Required - Expended Extract Date  -  YYYYMMDD  - column 387-394      (8)"
    self.edit38.SetToolTip(wx.ToolTip(prompt))                
    self.edit38.SetBackgroundColour((166,244,244))  # cyan


    wx.StaticText(self, -1, "NENA Reserved", pos=wx.Point(108, 320))
    self.edit39 = wx.TextCtrl(self, -1, value='', pos=wx.Point(108, 340), size=wx.Size(540, 20))
    self.edit39.SetMaxLength(81)
    prompt = "NENA Reserved - PSAP  Comment   -  column 395-475        (81)"
    self.edit39.SetToolTip(wx.ToolTip(prompt))                
    self.edit39.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "CID 2", pos=wx.Point(670, 320))
    self.edit40 = wx.TextCtrl(self, -1, value='', pos=wx.Point(670, 340), size=wx.Size(50, 20))
    self.edit40.SetMaxLength(5)
    prompt = "Data Provider ID (Company ID 2)   -  column 476-480        (5)"
    self.edit40.SetToolTip(wx.ToolTip(prompt))                
    self.edit40.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Reserved-2", pos=wx.Point(15, 380))
    self.edit41 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 400), size=wx.Size(220, 20))
    self.edit41.SetMaxLength(31)
    prompt = "Reserved for Database   -  column 481-511        (31)"
    self.edit41.SetToolTip(wx.ToolTip(prompt))                
    self.edit41.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "EOR", pos=wx.Point(250, 380))
    self.edit42 = wx.TextCtrl(self, -1, value='*', pos=wx.Point(250, 400), size=wx.Size(20, 20))
    self.edit42.SetMaxLength(1)
    prompt = "Required - End of record   -  column  512        (1)"
    self.edit42.SetToolTip(wx.ToolTip(prompt))                
    self.edit42.SetBackgroundColour((166,244,244))  # cyan 


def Define_ALI_fields(self):
    """
    Define ALI record field names
    """
    FOC = self.edit1.GetValue().ljust(1)
    NPA = self.edit2.GetValue().ljust(3) 
    TN = self.edit3.GetValue().ljust(7)
    HNum = self.edit4.GetValue().ljust(10)
    HNumSuffix = self.edit5.GetValue().ljust(4)
            
    PrDir = self.edit6.GetValue().ljust(2)
    streetname = self.edit7.GetValue().ljust(60)
    SSfx = self.edit8.GetValue().ljust(4)
            
    PoDir = self.edit9.GetValue().ljust(2)
    community = self.edit10.GetValue().ljust(32)
    ST = self.edit11.GetValue().ljust(2)
            
    location = self.edit12.GetValue().ljust(60)
    customername = self.edit13.GetValue().ljust(32)
    CLS = self.edit14.GetValue().ljust(1)
    TOS = self.edit15.GetValue().ljust(1)
    XCH = self.edit16.GetValue().ljust(4)
            
    ESN = self.edit17.GetValue().ljust(5)
    MNPA = self.edit18.GetValue().ljust(3)
    Main = self.edit19.GetValue().ljust(7)
    OrderNo = self.edit20.GetValue().ljust(10)
            
    ExDate = self.edit21.GetValue().ljust(6)
    COID = self.edit22.GetValue().ljust(4)
    CID1 = self.edit23.GetValue().ljust(5)
            
    SID = self.edit24.GetValue().ljust(1)
    ZIP = self.edit25.GetValue().ljust(5)
            
    ZIP4 = self.edit26.GetValue().ljust(4)
    general = self.edit27.GetValue().ljust(11)
    CCD = self.edit28.GetValue().ljust(3)
            
    comments = self.edit29.GetValue().ljust(30)
    XLON = self.edit30.GetValue().ljust(9)
    YLAT = self.edit31.GetValue().ljust(9)
    Zcoord = self.edit32.GetValue().ljust(5)
            
    CellID = self.edit33.GetValue().ljust(6)
    SecID = self.edit34.GetValue().ljust(1)
    TAR = self.edit35.GetValue().ljust(6)

    reserved1 = self.edit36.GetValue().ljust(21)
    ALT = self.edit37.GetValue().ljust(10)
            
    EEDate = self.edit38.GetValue().ljust(8)
    NENAreserved = self.edit39.GetValue().ljust(81)
    CID2 = self.edit40.GetValue().ljust(5)
    reserved2 = self.edit41.GetValue().ljust(31)
    EOR = self.edit42.GetValue().ljust(1)
    
    """
    lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
        PoDir + community + ST + location + customername + CLS + TOS +   \
        XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
        SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
        Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
        NENAreserved + CID2 + reserved2 + EOR
    """

    return  FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,   \
            XCH,ESN,MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR        
                   


class Create_ALI_SO_Dialog(wx.Dialog):

    def __init__(self, parent, id=-1, title="ALI SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(760, 570))
        
        self.SetBackgroundColour((255,228,196))  # bisque
        
        # for display common messages on this dialog
        julianday = SO_utils.get_julianday()


        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(325, 460), size=wx.Size(185, 20))
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red,  38,210,189 = cyan, 255,255,197 = suds yellow,  166,244,244  = required fields
        self.label3.SetLabel("Today's Julian date is   %s\n" % julianday)


        # Get default values for new ALI record
        retvars = default_ALI_fields_for_new_record()

        FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
        MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                \
        SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR  = retvars

        Display_single_ALI_record_with_data(self,FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
                                            MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                 \
                                            SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR)
               
        self.button1 = wx.Button(self, wx.ID_OK, label="ADD current record to data file",
            pos=wx.Point(210, 500), size=wx.Size(185, 28))
        prompt = "ADD this current record to ALI SOI data file"
        self.button1.SetToolTip(wx.ToolTip(prompt)) 
        self.button1.SetBackgroundColour((217,255,219)) # vegaseat green


        self.button2 = wx.Button(self, wx.ID_CANCEL, label="Cancel",
            pos=wx.Point(420, 500), size=wx.Size(140, 28))
        prompt = "Cancel saving new ALI SOI data file"
        self.button2.SetToolTip(wx.ToolTip(prompt)) 
        self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
        # enter to tab, move to next field
        return_id = wx.NewId()
        acc_table = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, return_id)])
        self.SetAcceleratorTable(acc_table)
        wx.EVT_MENU(self, return_id, self.on_return)


        # respond to button click event
        self.button1.Bind(wx.EVT_BUTTON, self.button1Click, self.button1)

        # respond to button click event
        self.button2.Bind(wx.EVT_BUTTON, self.onCancel, self.button2)
     
       
    def button1Click(self,event):
        """SAVE modified ALI SO DAT file button has been clicked"""

        try:
            # string of record to build
            lineout = []
            
            retFieldNames = Define_ALI_fields(self)

            FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,   \
            XCH,ESN,MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR  = retFieldNames                   

            # building the record
            lineout = FOC + NPA + TN + HNum + HNumSuffix + PrDir + streetname + SSfx + \
                   PoDir + community + ST + location + customername + CLS + TOS +   \
                   XCH + ESN + MNPA + Main + OrderNo + ExDate + COID + CID1 +       \
                   SID + ZIP + ZIP4 + general + CCD + comments + XLON + YLAT +      \
                   Zcoord + CellID + SecID + TAR + reserved1 + ALT + EEDate +       \
                   NENAreserved + CID2 + reserved2 + EOR           

            try:
                # write current record to temp ALI SOI data file
                with open(ALIpath,"a") as A_datfile:
                    A_datfile.write(str(lineout) + '\n')

                SO_utils.MsgBox("Current record has been added to file\n   %s" % A_datfile,"Current record has been added to file")
            except:
                print "Exception in writing ALI record to  %s\n" % A_datfile


            #Refresh_ALI_self_edit(self)                      
            # Get default values for new ALI record
            retvars = default_ALI_fields_for_new_record()

            FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
            MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                \
            SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR  = retvars

            Display_single_ALI_record_with_data(self,FOC,NPA,TN,HNum,HNumSuffix,PrDir,streetname,SSfx,PoDir,community,ST,location,customername,CLS,TOS,XCH,ESN,   \
                                                MNPA,Main,OrderNo,ExDate,COID,CID1,SID,ZIP,ZIP4,general,CCD,comments,XLON,YLAT,Zcoord,CellID,                 \
                                                SecID,TAR,reserved1,ALT,EEDate,NENAreserved,CID2,reserved2,EOR)

        except:
            print "Exception button1click - Create_ALI_SO_Dialog"
            self.Destroy()


    def onCancel(self, event):
        ## close ALI data file    No need since using  with open()
        #A_datfile.close()

        self.result = None
        self.Destroy()
        
    def on_return(self, event):
        """
        Enter to tab, move to next field
        """
        ctl = wx.Window_FindFocus()
        ctl.Navigate()



def Display_single_MSAG_record_with_data(self, PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,     \
                                               XCH,general,TAR,FOC,reserved,EExDate,EOR):
    """
    Display fields of single MSAG record fill with data
    """
    wx.StaticText(self, -1, "PrDir", pos=wx.Point(15, 20))
    self.edit1 = wx.TextCtrl(self, -1, value=PrDir, pos=wx.Point(15, 40), size=wx.Size(30, 20))
    self.edit1.SetMaxLength(2)
    prompt = "Prefix Directional - column 1-2     (2)"
    self.edit1.SetToolTip(wx.ToolTip(prompt))
    self.edit1.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Street Name", pos=wx.Point(55, 20))
    self.edit2 = wx.TextCtrl(self, -1, value=streetname, pos=wx.Point(55, 40), size=wx.Size(365, 20))
    self.edit2.SetMaxLength(60)
    prompt = "Required - Street Name - column 3-62      (60)"
    self.edit2.SetToolTip(wx.ToolTip(prompt))
    self.edit2.SetBackgroundColour((166,244,244))  # suds yellow
        
    wx.StaticText(self, -1, "StSffx", pos=wx.Point(425, 20))
    self.edit3 = wx.TextCtrl(self, -1, value=StSffx, pos=wx.Point(425, 40), size=wx.Size(35, 20))
    self.edit3.SetMaxLength(4)
    prompt = "Street Suffix   - column 63-66     (4)"
    self.edit3.SetToolTip(wx.ToolTip(prompt))
    self.edit3.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "PoDir", pos=wx.Point(465, 20))
    self.edit4 = wx.TextCtrl(self, -1, value=PoDir, pos=wx.Point(465, 40), size=wx.Size(30, 20))
    self.edit4.SetMaxLength(2)
    prompt = "Post Directional    - column 67-68     (2)"
    self.edit4.SetToolTip(wx.ToolTip(prompt))
    self.edit4.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Low", pos=wx.Point(500, 20))
    self.edit5 = wx.TextCtrl(self, -1, value=Low, pos=wx.Point(500, 40), size=wx.Size(80, 20))
    self.edit5.SetMaxLength(10)
    prompt = "Required - Low Range    - column 69-78     (10)"
    self.edit5.SetToolTip(wx.ToolTip(prompt))
    self.edit5.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "High", pos=wx.Point(595, 20))
    self.edit6 = wx.TextCtrl(self, -1, value=High, pos=wx.Point(595, 40), size=wx.Size(80, 20))
    self.edit6.SetMaxLength(10)
    prompt = "Required - High Range    - column 79-88     (10)"
    self.edit6.SetToolTip(wx.ToolTip(prompt))
    self.edit6.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "MSAG Community", pos=wx.Point(15, 80))
    self.edit7 = wx.TextCtrl(self, -1, value=MSAGcomm, pos=wx.Point(15, 100), size=wx.Size(220, 20))
    self.edit7.SetMaxLength(32)
    prompt = "Required - MSAG Community    - column 89-120     (32)"
    self.edit7.SetToolTip(wx.ToolTip(prompt))
    self.edit7.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "ST", pos=wx.Point(250, 80))
    self.edit8 = wx.TextCtrl(self, -1, value=ST, pos=wx.Point(250, 100), size=wx.Size(30, 20))
    self.edit8.SetMaxLength(2)
    prompt = "Required - State     -  column 121-122     (2)"
    self.edit8.SetToolTip(wx.ToolTip(prompt))
    self.edit8.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "OE", pos=wx.Point(290, 80))
    self.edit9 = wx.TextCtrl(self, -1, value=oddeven, pos=wx.Point(290, 100), size=wx.Size(20, 20))
    self.edit9.SetMaxLength(1)
    prompt = "Required - Odd / Even     -  column 123     (1)"
    self.edit9.SetToolTip(wx.ToolTip(prompt))
    self.edit9.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "ESN", pos=wx.Point(320, 80))
    self.edit10 = wx.TextCtrl(self, -1, value=ESN, pos=wx.Point(320, 100), size=wx.Size(60, 20))
    self.edit10.SetMaxLength(5)
    prompt = "Required - ESN     -   column 124-128      (5)"
    self.edit10.SetToolTip(wx.ToolTip(prompt))
    self.edit10.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "ExDate", pos=wx.Point(395, 80))
    self.edit11 = wx.TextCtrl(self, -1, value=ExDate, pos=wx.Point(395, 100), size=wx.Size(60, 20))
    self.edit11.SetMaxLength(6)
    prompt = "Required - Extract Date   MMDDYY     -   column 129-134      (6)"
    self.edit11.SetToolTip(wx.ToolTip(prompt))
    self.edit11.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "PSAP ID", pos=wx.Point(465, 80))
    self.edit12 = wx.TextCtrl(self, -1, value=PSAPid, pos=wx.Point(465, 100), size=wx.Size(40, 20))
    self.edit12.SetMaxLength(4)
    prompt = "PSAP ID     -   column 135-138      (4)"
    self.edit12.SetToolTip(wx.ToolTip(prompt))
    self.edit12.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "COID", pos=wx.Point(525, 80))
    self.edit13 = wx.TextCtrl(self, -1, value=COID, pos=wx.Point(525, 100), size=wx.Size(40, 20))
    self.edit13.SetMaxLength(4)
    prompt = "Required - County  ID     -   column 139-142      (4)"
    self.edit13.SetToolTip(wx.ToolTip(prompt))
    self.edit13.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "XCH", pos=wx.Point(595, 80))
    self.edit14 = wx.TextCtrl(self, -1, value=XCH, pos=wx.Point(595, 100), size=wx.Size(40, 20))
    self.edit14.SetMaxLength(4)
    prompt = "Exchange     -   column 143-146      (4)"
    self.edit14.SetToolTip(wx.ToolTip(prompt))
    self.edit14.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "General", pos=wx.Point(15, 140))
    self.edit15 = wx.TextCtrl(self, -1, value=general, pos=wx.Point(15, 160), size=wx.Size(140, 20))
    self.edit15.SetMaxLength(20)
    prompt = "General Use  - column 147-166     (20)"
    self.edit15.SetToolTip(wx.ToolTip(prompt))                
    self.edit15.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "TAR", pos=wx.Point(170, 140))
    self.edit16 = wx.TextCtrl(self, -1, value=TAR, pos=wx.Point(170, 160), size=wx.Size(60, 20))
    self.edit16.SetMaxLength(6)
    prompt = "TAR Code   - column 167-172     (6)"
    self.edit16.SetToolTip(wx.ToolTip(prompt))                
    self.edit16.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "FOC", pos=wx.Point(250, 140))
    self.edit17 = wx.TextCtrl(self, -1, value=FOC, pos=wx.Point(250, 160), size=wx.Size(20, 20))
    self.edit17.SetMaxLength(1)
    prompt = "Required - Valid Function Of Change:  D(Delete), I(Insert), B(Before), A(After)  - column 173     (1)"
    self.edit17.SetToolTip(wx.ToolTip(prompt))                
    self.edit17.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "Reserved", pos=wx.Point(280, 140))
    self.edit18 = wx.TextCtrl(self, -1, value=reserved, pos=wx.Point(280, 160), size=wx.Size(120, 20))
    self.edit18.SetMaxLength(18)
    prompt = "Reserved    - column 174-191     (18)"
    self.edit18.SetToolTip(wx.ToolTip(prompt))                
    self.edit18.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "EExDate", pos=wx.Point(415, 140))
    self.edit19 = wx.TextCtrl(self, -1, value=EExDate, pos=wx.Point(415, 160), size=wx.Size(80, 20))
    self.edit19.SetMaxLength(8)
    prompt = "Expanded Extract Date  YYYYMMDD   - column 192-199     (8)"
    self.edit19.SetToolTip(wx.ToolTip(prompt))                
    self.edit19.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "EOR", pos=wx.Point(520, 140))
    self.edit20 = wx.TextCtrl(self, -1, value=EOR, pos=wx.Point(520, 160), size=wx.Size(20, 20))
    self.edit20.SetMaxLength(1)
    prompt = "Required - End of record   -  column  200        (1)"
    self.edit20.SetToolTip(wx.ToolTip(prompt))                
    self.edit20.SetBackgroundColour((166,244,244))  # suds yellow  


    # get value out from text edit field, remove trailing spaces, then set value back to the edit field
    PrDir = self.edit1.GetValue().strip()
    self.edit1.SetValue(PrDir)

    streetname = self.edit2.GetValue().strip()
    self.edit2.SetValue(streetname)

    StSffx = self.edit3.GetValue().strip()
    self.edit3.SetValue(StSffx)

    PoDir = self.edit4.GetValue().strip()
    self.edit4.SetValue(PoDir)

    Low = self.edit5.GetValue().strip()
    self.edit5.SetValue(Low)

    High = self.edit6.GetValue().strip()
    self.edit6.SetValue(High)

    MSAGcomm = self.edit7.GetValue().strip()
    self.edit7.SetValue(MSAGcomm)

    ST = self.edit8.GetValue().strip()
    self.edit8.SetValue(ST)

    oddeven = self.edit9.GetValue().strip()
    self.edit9.SetValue(oddeven)

    ESN = self.edit10.GetValue().strip()
    self.edit10.SetValue(ESN)

    ExDate = self.edit11.GetValue().strip()
    self.edit11.SetValue(ExDate)

    PSAPid = self.edit12.GetValue().strip()
    self.edit12.SetValue(PSAPid)

    COID = self.edit13.GetValue().strip()
    self.edit13.SetValue(COID)

    XCH = self.edit14.GetValue().strip()
    self.edit14.SetValue(XCH)

    general = self.edit15.GetValue().strip()
    self.edit15.SetValue(general)

    TAR = self.edit16.GetValue().strip()
    self.edit16.SetValue(TAR)

    FOC = self.edit17.GetValue().strip()
    self.edit17.SetValue(FOC)

    reserved = self.edit18.GetValue().strip()
    self.edit18.SetValue(reserved)

    EExDate = self.edit19.GetValue().strip()
    self.edit19.SetValue(EExDate)

    EOR = self.edit20.GetValue().strip()
    self.edit20.SetValue(EOR)
        
    ## set max length allowed for all fields
    #self.edit1.SetMaxLength(2)
    #self.edit2.SetMaxLength(60)
    #self.edit3.SetMaxLength(4)
    #self.edit4.SetMaxLength(2)
    #self.edit5.SetMaxLength(10)
    #self.edit6.SetMaxLength(10)
    #self.edit7.SetMaxLength(32)
    #self.edit8.SetMaxLength(2)
    #self.edit9.SetMaxLength(1)
    #self.edit10.SetMaxLength(5)
    #self.edit11.SetMaxLength(6)
    #self.edit12.SetMaxLength(4)
    #self.edit13.SetMaxLength(4)
    #self.edit14.SetMaxLength(4)
    #self.edit15.SetMaxLength(20)
    #self.edit16.SetMaxLength(6)
    #self.edit17.SetMaxLength(1)
    #self.edit18.SetMaxLength(18)
    #self.edit19.SetMaxLength(8)
    #self.edit20.SetMaxLength(1)



class Edit_MSAG_SO_Dialog(wx.Dialog):

    def __init__(self, parent, id=-1, title="MSAG SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(780, 580))
        self.SetBackgroundColour((255,228,196))  # bisque

        self.list_ctrl = EditableListCtrl(self, size=(-1, 250), style=wx.LC_REPORT)
        self.list_ctrl.SetBackgroundColour((217,255,219)) # vegaseat green

        # read data from MSAG file
        retvars = Read_from_MSAG_file()
        dline, reccount, selectedpath, selectedfile, currpath, elapsedtime = retvars
                
        # insert ALI columns to list ctrl
        insert_MSAG_column_to_list_ctrl(self)

        # build self.myRowDict dictionary from dline dictionary
        index = 0
        #self.myRowDict = {}
        rcnt = 1        
        for key in sorted(dline):
            if dline.has_key(str(key)):                
                line = dline[str(key)]                
                #self.myRowDict[index] = line

                if ((reccount >= 1) and ((len(line) == (MSAG_REC_LEN + 1)) or (len(line) == MSAG_REC_LEN))):
                    # # prepare more than one records
                    retvars = obtain_MSAG_fields_from_line(line)

                    PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
                    ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR = retvars

                    insert_string_MSAG_items_to_list_ctrl(self, index, PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
                                                                       ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR)
                                        
                else:
                    SO_utils.MsgBox("Invalid MSAG SOI data file","Invalid Data")
                    self.result = None
                    self.Destroy()
                    
                index += 1               
                rcnt += 1
                
            else:
                print 'NONE'

        #print self.myRowDict

        # self.label2 = status message
        self.label2 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label2.SetForegroundColour((50,30,236))       # 225,40,82 = red

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Total of  %d  record(s) loaded in  %f  seconds." % (reccount, elapsedtime))
        self.label3.Refresh()

        self.label4 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label4.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label4.SetLabel("Editing data file  %s   in   [%s]" % (selectedfile, selectedpath))
        self.label4.Refresh()
        
        self.saveBtn = wx.Button(self, wx.ID_ANY, "SAVE MSAG records")
        self.saveBtn.Bind(wx.EVT_BUTTON, self.OnButtonClicked)
        self.saveBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        
        self.cancelBtn = wx.Button(self, wx.ID_ANY, "Cancel")
        self.cancelBtn.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.cancelBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        
        # Create some sizers
        mainSizer = wx.BoxSizer(wx.VERTICAL)        
        mainSizer.Add(self.list_ctrl, 1, wx.ALL|wx.EXPAND, 5)
        mainSizer.Add(self.label2, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label3, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label4, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.saveBtn, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.cancelBtn, 0, wx.ALL|wx.CENTER, 5)        
        self.SetSizer(mainSizer)


    def OnButtonClicked(self, e):
        """
        loop through all the rows,  item.GetText() for all columns on each row
        """
        self.saveBtn.Disable()

        start = time.time()                               # start the stopwatch
        print "start timing:  %f" % start
        time.clock()

        count = self.list_ctrl.GetItemCount()
        for row in range(count):            
            # get values of every columns in current row
            lineout = GetText_from_MSAG_columns_currRow(self, row)
            
            try:
                # write current record to temp MSAG SOI data file
                with open(MSAGpath,"a") as M_datfile:
                    M_datfile.write(str(lineout) + '\n')

                    self.label2.SetLabel("Processing ......... %d   of  %d" % (row, count))
                    self.label2.Refresh()
                    
            except:
                print "Exception in writing MSAG record to  %s\n" % M_datfile

        elapsedtime = time.time() - start                  # end timing
        print "end timing:  %f" % elapsedtime

        self.label2.SetLabel("Elapsed time = %f  seconds" % elapsedtime)
        self.label2.Refresh()

        SO_utils.MsgBox("%s  records were added to file\n   %s    in   %s   seconds" % (count,M_datfile, elapsedtime),"Current records were added to file")
        self.Destroy()  

    def OnCancel(self, e):
        self.result = None
        self.Destroy()        


########################################################################
class MSAG(object):
    def __init__(self, PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN, ExDate, PSAPid, COID, XCH,   \
                       general, TAR, FOC, reserved, EExDate, EOR):
        
        self.PrDir = PrDir
        self.streetname = streetname
        self.StSffx = StSffx
        self.PoDir = PoDir
        self.Low = Low
        self.High = High
        self.MSAGcomm = MSAGcomm
        self.ST = ST
        self.oddeven = oddeven
        self.ESN = ESN
        self.ExDate = ExDate
        self.PSAPid = PSAPid
        self.COID = COID
        self.XCH = XCH
        self.general = general
        self.TAR = TAR
        self.FOC = FOC
        self.reserved = reserved
        self.EExDate = EExDate
        self.EOR = EOR


#######################################################################
def set_MSAG_columns(self, data=None):
    """
       PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
       ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR
    """
    self.dataOlv.SetColumns([
            
    ColumnDefn("Prefix Directional  (Col: 1 - 2, max = 2)", "left", 60, "PrDir"),
    ColumnDefn("Street Name  (Col: 3 - 62, max = 60)", "left", 200, "streetname"),
    ColumnDefn("Street Suffix  (Col: 63 - 66, max = 4)", "left", 60, "StSffx"),
    ColumnDefn("Post Directory  (Col: 67 - 68, max = 2)", "left", 60, "PoDir"),
    ColumnDefn("Low Range  (Col: 69 - 78, max = 10)", "left", 80, "Low"),
    ColumnDefn("High Range  (Col: 79 - 88, max = 10)", "left", 80, "High"),
    ColumnDefn("MSAG Community  (Col: 89 - 120, max = 32)", "left", 180, "MSAGcomm"),
    ColumnDefn("State  (Col: 121 - 122, max = 2)", "left", 40, "ST"),
    ColumnDefn("Odd-Even  (Col: 123, max = 1)", "left", 40, "oddeven"),
    ColumnDefn("ESN  (Col: 124 - 128, max = 5)", "left", 80, "ESN"),
    ColumnDefn("Extract Date  (Col: 129 - 134, max = 6)", "left", 100, "ExDate"),
    ColumnDefn("PSAP ID  (Col: 135 - 138, max = 4)", "left", 100, "PSAPid"),
    ColumnDefn("County ID  (Col: 139 - 142, max = 4)", "left", 100, "COID"),
    ColumnDefn("Exchange  (Col: 143 - 146, max = 4)", "left", 60, "XCH"),
    ColumnDefn("General Use  (Col: 147 - 166, max = 4)", "left", 220, "general"),
    ColumnDefn("TAR Code  (Col: 167 - 172, max = 6)", "left", 60, "TAR"),
    ColumnDefn("Function of Change  (Col: 173, max = 1)", "left", 120, "FOC"),
    ColumnDefn("Reserved  (Col: 174 - 191, max = 18)", "left", 180, "reserved"),
    ColumnDefn("Expanded Extracted Date  (Col: 192 - 199, max = 8", "left", 120, "EExDate"),
    ColumnDefn("EOR  (Col: 200, max = 1)", "left", 40, "EOR")
            
    ])

    self.dataOlv.CreateCheckStateColumn()

    #self.olv1.SetColumnFixedWidth(0, 16)    # the first column is fixed to 16 pixel wide
    #self.titleColumn.minimumWidth = 30      # will stop the "Title" column from becoming less than 30 pixels in width
    #self.titleColumn.maximumWidth = 120     # will set the "Title" column from becoming more than 120 pixels in width
    #self.statusColumn = ColumnDefn("", imageGetter=statusImageGetter, fixedWidth=16)     # make a column be fixed width and unresizable by the user


##############################################
class Edit_MSAG_SO_Dialog_OLV(wx.Dialog):

    def __init__(self, parent, id=-1, title="MSAG SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(780, 580))
        self.SetBackgroundColour((255,228,196))  # bisque

        # read data from ALI file
        retvars = Read_from_MSAG_file_OLV()
        line, dline, reccount, selectedpath, selectedfile, currpath, elapsedtime = retvars

        # obtain ALI fields from line
        retvars = obtain_MSAG_fields_from_line(line)
                
        PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
        ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR  = retvars
        
        self.dataOlv = ObjectListView(self, wx.ID_ANY, style=wx.LC_REPORT|wx.SUNKEN_BORDER)        
        # Allow the cell values to be edited when double-clicked
        self.dataOlv.cellEditMode = ObjectListView.CELLEDIT_SINGLECLICK
        self.dataOlv.SetBackgroundColour((217,255,219)) # vegaseat green

        set_MSAG_columns(self)

        index = 0
        rcnt = 1        
        for key in sorted(dline):
            if dline.has_key(str(key)):                
                line = dline[str(key)]                

                #print "line = [%s]\n" % line

                if ((reccount >= 1) and ((len(line) == (MSAG_REC_LEN + 1) or (len(line) == MSAG_REC_LEN)))):
                    # prepare more than one records
                    retvars2 = obtain_MSAG_fields_from_line(line)
        
                    PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
                    ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR  = retvars2

                    self.MSAGrecord = [MSAG(PrDir, streetname, StSffx, PoDir, Low, High, MSAGcomm, ST, oddeven, ESN,   \
                                            ExDate, PSAPid, COID, XCH, general, TAR, FOC, reserved, EExDate, EOR)]

                    self.dataOlv.AddObjects(self.MSAGrecord)
                                      
                else:
                    SO_utils.MsgBox("Invalid MSAG SOI data file","Invalid Data")
                    self.result = None
                    self.Destroy()
                    
                index += 1               
                rcnt += 1

            else:
                print 'NONE'

        #print self.myRowDict

        # self.label2 = status message
        self.label2 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label2.SetForegroundColour((50,30,236))       # 225,40,82 = red

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Total of  %d  record(s) loaded in  %f  seconds." % (reccount, elapsedtime))
        self.label3.Refresh()

        self.label4 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(125, 460), size=wx.Size(-1, -1))
        # set foreground blue
        self.label4.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label4.SetLabel("Editing data file  %s   in   [%s]" % (selectedfile, selectedpath))
        self.label4.Refresh()
        
        self.saveBtn = wx.Button(self, wx.ID_ANY, "SAVE current items on the list to data file")
        self.saveBtn.SetToolTipString("SAVE current items on the list to data file")
        self.saveBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        self.saveBtn.Bind(wx.EVT_BUTTON, self.OnButtonClicked)

        self.deleteBtn = wx.Button(self, wx.ID_ANY, "Remove items from list")
        self.deleteBtn.SetToolTipString("Check to select one or many item(s) on the list, then click 'Remove items from list' ")
        self.deleteBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.OnDelete)

        self.cancelBtn = wx.Button(self, wx.ID_ANY, "Cancel")
        self.cancelBtn.SetToolTipString("Discard changes of current items on the list")
        self.cancelBtn.SetBackgroundColour((217,255,219)) # vegaseat green
        self.cancelBtn.Bind(wx.EVT_BUTTON, self.OnCancel)
        
        # Create some sizers
        mainSizer = wx.BoxSizer(wx.VERTICAL)        
        mainSizer.Add(self.dataOlv, 1, wx.ALL|wx.EXPAND, 5)
        mainSizer.Add(self.label2, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label3, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.label4, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.saveBtn, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.deleteBtn, 0, wx.ALL|wx.CENTER, 5)
        mainSizer.Add(self.cancelBtn, 0, wx.ALL|wx.CENTER, 5)
                
        self.SetSizer(mainSizer)


    def OnButtonClicked(self, e):
        """
        loop through all the rows,  item.GetText() for all columns on each row
        """
        self.saveBtn.Disable()

        """ Save edited records to file """        
        # Save away the edited text        
        dlg = wx.FileDialog(
                    None, message="Save file as ...",
                    defaultDir=".",
                    defaultFile="", wildcard="*.dat", style=wx.SAVE
                    )
        if dlg.ShowModal() == wx.ID_OK:      
                # Open the file for write, write, close
                filename = dlg.GetFilename()
                dirname = dlg.GetDirectory()
                filehandle = open(os.path.join(dirname, filename),'w')
        # Get rid of the dialog to keep things tidy
        dlg.Destroy()

        start = time.time()                               # start the stopwatch
        print "start timing:  %f" % start
        time.clock()

        count = self.dataOlv.GetItemCount()
        for row in range(count):            
            # get values of every columns in current row
            lineout = GetText_from_MSAG_columns_currRow_OLV_3(self, row)
            
            try:
                ## write current record to temp MSAG SOI data file
                #with open(MSAGpath,"a") as M_datfile:
                #    M_datfile.write(str(lineout) + '\n')

                #    self.label2.SetLabel("Processing ......... %d   of  %d" % (row, count))
                #    self.label2.Refresh()
                
                filehandle.write(str(lineout) + '\n')
                self.label2.SetLabel("Processing ......... %d   of  %d" % (row, count))
                self.label2.Refresh()
                    
            except:
                print "Exception in writing MSAG record to  %s\n" % filename

        filehandle.close()

        elapsedtime = time.time() - start                  # end timing
        print "end timing:  %f" % elapsedtime

        self.label2.SetLabel("Elapsed time = %f  seconds" % elapsedtime)
        self.label2.Refresh()

        SO_utils.MsgBox("%s  records were added to file\n   %s    in   %s   seconds" % (count,filename, elapsedtime),"Current records were added to file")
        self.Destroy()  


    def OnDelete(self, e):
        objects = self.dataOlv.GetObjects()
        
        for obj in objects:
            if (self.dataOlv.GetCheckState(obj)):
                 print "\nRemove Low = %s - High = %s - Street name = %s  from the list." % (obj.Low, obj.High, obj.streetname)
                 self.dataOlv.RemoveObject(obj)
            
        self.dataOlv.RefreshObjects(objects)        
        e.Skip()


    def OnCancel(self, e):
        self.result = None
        self.Destroy()        



def Load_MSAG_SO_File():
    """
    Load MSAG SO dat file (length 200)
    """
    try:
       line = []
       
       #selected_MSAG_datfilename = Select_MSAG_dat_file()
       #currpath = os.getcwd()
                                                   
       extension_list = ['dat', 'DAT']
       prefixed = 'DMSAG'
       selected_MSAG_datfilename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
       selectedpath, selectedfile = selected_MSAG_datfilename
       currpath = selectedpath + "\\" + selectedfile
       
       if (os.path.exists(currpath)):
           dfile = open(currpath, 'r')
           line = dfile.read(MSAG_REC_LENGTH)

       return line, selectedpath, selectedfile   
       dfile.close()
       
    except:
       print "Exception loading ALI SO dat file"
       return line, selectedpath, selectedfile

       
def Select_MSAG_dat_file():
    try:
        extension_list = ['dat','DAT']
        prefixed = 'DMSAG'

        listDATfilenames_w_extension = SO_utils.get_filenames_filter_startswith_and_extensions(prefixed, extension_list)
        selectedfilename =""
        datdlg = wx.SingleChoiceDialog( None,
                                        "Select a DAT file",
                                        "Listing of available DAT files", listDATfilenames_w_extension, wx.CHOICEDLG_STYLE)
        if (datdlg.ShowModal() == wx.ID_OK):
            selectedfilename = datdlg.GetStringSelection()                

        datdlg.Destroy()
        return selectedfilename

    except:
        print "Cancel was pressed in Select_MSAG_dat_file"
 
              
#######################################
def Display_single_MSAG_record(self):
    """
    Display single MSAG record fields
    """
    # required fields color = (166,244,244)

    wx.StaticText(self, -1, "PrDir:", pos=wx.Point(15, 20))
    self.edit1 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 40), size=wx.Size(30, 20))
    self.edit1.SetMaxLength(2)
    prompt = "Prefix Directional - column 1-2     (2)"
    self.edit1.SetToolTip(wx.ToolTip(prompt))
    self.edit1.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "Street Name:", pos=wx.Point(55, 20))
    self.edit2 = wx.TextCtrl(self, -1, value='', pos=wx.Point(55, 40), size=wx.Size(365, 20))
    self.edit2.SetMaxLength(60)
    prompt = "Required - Street Name - column 3-62      (60)"
    self.edit2.SetToolTip(wx.ToolTip(prompt))
    self.edit2.SetBackgroundColour((166,244,244))  # suds yellow

        
    wx.StaticText(self, -1, "StSffx:", pos=wx.Point(425, 20))
    self.edit3 = wx.TextCtrl(self, -1, value='', pos=wx.Point(425, 40), size=wx.Size(35, 20))
    self.edit3.SetMaxLength(4)
    prompt = "Street Suffix   - column 63-66     (4)"
    self.edit3.SetToolTip(wx.ToolTip(prompt))
    self.edit3.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "PoDir:", pos=wx.Point(465, 20))
    self.edit4 = wx.TextCtrl(self, -1, value='', pos=wx.Point(465, 40), size=wx.Size(30, 20))
    self.edit4.SetMaxLength(2)
    prompt = "Post Directional    - column 67-68     (2)"
    self.edit4.SetToolTip(wx.ToolTip(prompt))
    self.edit4.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "Low:", pos=wx.Point(500, 20))
    self.edit5 = wx.TextCtrl(self, -1, value='', pos=wx.Point(500, 40), size=wx.Size(80, 20))
    self.edit5.SetMaxLength(10)
    prompt = "Required - Low Range    - column 69-78     (10)"
    self.edit5.SetToolTip(wx.ToolTip(prompt))
    self.edit5.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "High:", pos=wx.Point(595, 20))
    self.edit6 = wx.TextCtrl(self, -1, value='', pos=wx.Point(595, 40), size=wx.Size(80, 20))
    self.edit6.SetMaxLength(10)
    prompt = "Required - High Range    - column 79-88     (10)"
    self.edit6.SetToolTip(wx.ToolTip(prompt))
    self.edit6.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "MSAG Community:", pos=wx.Point(15, 80))
    self.edit7 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 100), size=wx.Size(220, 20))
    self.edit7.SetMaxLength(32)
    prompt = "Required - MSAG Community    - column 89-120     (32)"
    self.edit7.SetToolTip(wx.ToolTip(prompt))
    self.edit7.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "ST:", pos=wx.Point(250, 80))
    self.edit8 = wx.TextCtrl(self, -1, value='', pos=wx.Point(250, 100), size=wx.Size(30, 20))
    self.edit8.SetMaxLength(2)
    prompt = "Required - State     -  column 121-122     (2)"
    self.edit8.SetToolTip(wx.ToolTip(prompt))
    self.edit8.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "OE:", pos=wx.Point(290, 80))
    self.edit9 = wx.TextCtrl(self, -1, value='', pos=wx.Point(290, 100), size=wx.Size(20, 20))
    self.edit9.SetMaxLength(1)
    prompt = "Required - Odd / Even     -  column 123     (1)"
    self.edit9.SetToolTip(wx.ToolTip(prompt))
    self.edit9.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "ESN:", pos=wx.Point(320, 80))
    self.edit10 = wx.TextCtrl(self, -1, value='', pos=wx.Point(320, 100), size=wx.Size(60, 20))
    self.edit10.SetMaxLength(5)
    prompt = "Required - ESN     -   column 124-128      (5)"
    self.edit10.SetToolTip(wx.ToolTip(prompt))
    self.edit10.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "ExDate:", pos=wx.Point(395, 80))
    self.edit11 = wx.TextCtrl(self, -1, value='', pos=wx.Point(395, 100), size=wx.Size(60, 20))
    self.edit11.SetMaxLength(6)
    prompt = "Required - Extract Date  MMDDYY     -   column 129-134      (6)"
    self.edit11.SetToolTip(wx.ToolTip(prompt))
    self.edit11.SetBackgroundColour((166,244,244))  # suds yellow


    wx.StaticText(self, -1, "PSAP ID:", pos=wx.Point(465, 80))
    self.edit12 = wx.TextCtrl(self, -1, value='', pos=wx.Point(465, 100), size=wx.Size(40, 20))
    self.edit12.SetMaxLength(4)
    prompt = "PSAP ID     -   column 135-138      (4)"
    self.edit12.SetToolTip(wx.ToolTip(prompt))
    self.edit12.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "COID:", pos=wx.Point(525, 80))
    self.edit13 = wx.TextCtrl(self, -1, value='', pos=wx.Point(525, 100), size=wx.Size(40, 20))
    self.edit13.SetMaxLength(4)
    prompt = "Required - County  ID     -   column 139-142      (4)"
    self.edit13.SetToolTip(wx.ToolTip(prompt))
    self.edit13.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "XCH:", pos=wx.Point(595, 80))
    self.edit14 = wx.TextCtrl(self, -1, value='', pos=wx.Point(595, 100), size=wx.Size(40, 20))
    self.edit14.SetMaxLength(4)
    prompt = "Exchange     -   column 143-146      (4)"
    self.edit14.SetToolTip(wx.ToolTip(prompt))
    self.edit14.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "General:", pos=wx.Point(15, 140))
    self.edit15 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 160), size=wx.Size(140, 20))
    self.edit15.SetMaxLength(20)
    prompt = "General Use  - column 147-166     (20)"
    self.edit15.SetToolTip(wx.ToolTip(prompt))                
    self.edit15.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "TAR:", pos=wx.Point(170, 140))
    self.edit16 = wx.TextCtrl(self, -1, value='', pos=wx.Point(170, 160), size=wx.Size(60, 20))
    self.edit16.SetMaxLength(6)
    prompt = "TAR Code   - column 167-172     (6)"
    self.edit16.SetToolTip(wx.ToolTip(prompt))                
    self.edit16.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "FOC:", pos=wx.Point(250, 140))
    self.edit17 = wx.TextCtrl(self, -1, value='', pos=wx.Point(250, 160), size=wx.Size(20, 20))
    self.edit17.SetMaxLength(1)
    prompt = "Required - Valid Function Of Change:  D(Delete), I(Insert), B(Before), A(After)  - column 173     (1)"
    self.edit17.SetToolTip(wx.ToolTip(prompt))                
    self.edit17.SetBackgroundColour((166,244,244))  # suds yellow

    wx.StaticText(self, -1, "Reserved:", pos=wx.Point(280, 140))
    self.edit18 = wx.TextCtrl(self, -1, value='', pos=wx.Point(280, 160), size=wx.Size(120, 20))
    self.edit18.SetMaxLength(18)
    prompt = "Reserved    - column 174-191     (18)"
    self.edit18.SetToolTip(wx.ToolTip(prompt))                
    self.edit18.SetBackgroundColour((255,255,197))  # suds yellow

    wx.StaticText(self, -1, "EExDate:", pos=wx.Point(415, 140))
    self.edit19 = wx.TextCtrl(self, -1, value='', pos=wx.Point(415, 160), size=wx.Size(80, 20))
    self.edit19.SetMaxLength(8)
    prompt = "Expanded Extract Date  YYYYMMDD   - column 192-199     (8)"
    self.edit19.SetToolTip(wx.ToolTip(prompt))                
    self.edit19.SetBackgroundColour((255,255,197))  # suds yellow


    wx.StaticText(self, -1, "EOR:", pos=wx.Point(520, 140))
    self.edit20 = wx.TextCtrl(self, -1, value='*', pos=wx.Point(520, 160), size=wx.Size(20, 20))
    self.edit20.SetMaxLength(1)
    prompt = "Required - End of record   -  column  200        (1)"
    self.edit20.SetToolTip(wx.ToolTip(prompt))                
    self.edit20.SetBackgroundColour((166,244,244))  # suds yellow 



#######################################
def Define_MSAG_fields(self):    
    """
    Define MSAG fields for new MSAG record
    """
    PrDir =  self.edit1.GetValue().ljust(2)
    streetname = self.edit2.GetValue().ljust(60)
    StSffx = self.edit3.GetValue().ljust(4)
    PoDir = self.edit4.GetValue().ljust(2)
    Low = self.edit5.GetValue().ljust(10)
    High = self.edit6.GetValue().ljust(10)
    MSAGcomm = self.edit7.GetValue().ljust(32)
    ST = self.edit8.GetValue().ljust(2)
    oddeven =  self.edit9.GetValue().ljust(1)
    ESN = self.edit10.GetValue().ljust(5)
    ExDate = self.edit11.GetValue().ljust(6)
    PSAPid = self.edit12.GetValue().ljust(4)
    COID = self.edit13.GetValue().ljust(4)
    XCH = self.edit14.GetValue().ljust(4)
    general = self.edit15.GetValue().ljust(20)
    TAR = self.edit16.GetValue().ljust(6)
    FOC = self.edit17.GetValue().ljust(1)
    reserved = self.edit18.GetValue().ljust(18)
    EExDate = self.edit19.GetValue().ljust(8)
    EOR = self.edit20.GetValue().ljust(1)
    
    """
    lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                TAR + FOC + reserved + EExDate + EOR
    """
    return PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,XCH,general,TAR,FOC,reserved,EExDate,EOR




#######################################
def default_MSAG_fields_for_new_record():    
    """
    Default data values for new MSAG record
    """
    PrDir =  "  " #self.edit1.GetValue().ljust(2)
    streetname = "123456789-123456789-123456789-123456789-123456789-123456789-"  #self.edit2.GetValue().ljust(60)
    StSffx = "    "  #self.edit3.GetValue().ljust(4)
    PoDir = "  "   #self.edit4.GetValue().ljust(2)
    Low = "1234567890"  #self.edit5.GetValue().ljust(10)
    High = "1234567890"  #self.edit6.GetValue().ljust(10)
    MSAGcomm = "123456789-123456789-123456789-12"  #self.edit7.GetValue().ljust(32)
    ST = "TN"   #self.edit8.GetValue().ljust(2)
    oddeven =  "B"  #self.edit9.GetValue().ljust(1)
    ESN = "12345"      #self.edit10.GetValue().ljust(5)
    ExDate = "MMDDYY"  #self.edit11.GetValue().ljust(6)
    PSAPid = "1234"    #self.edit12.GetValue().ljust(4)
    COID = "1234"      #self.edit13.GetValue().ljust(4)
    XCH = "1234"       #self.edit14.GetValue().ljust(4)
    general = "123456789-123456789-"   #self.edit15.GetValue().ljust(20)
    TAR = "123456"  #self.edit16.GetValue().ljust(6)
    FOC = "I"   #self.edit17.GetValue().ljust(1)
    reserved = "123456789-12345678"   #self.edit18.GetValue().ljust(18)
    EExDate = "YYYYMMDD"    #self.edit19.GetValue().ljust(8)
    EOR = "*"    #self.edit20.GetValue().ljust(1)
    
    """
    lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                TAR + FOC + reserved + EExDate + EOR
    """
    return PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,XCH,general,TAR,FOC,reserved,EExDate,EOR


def Refresh_MSAG_self_edit(self):
    """
    Re-initialize MSAG self.edit.. Values
    """
    self.edit1.Value = ''
    self.edit1.Refresh()

    self.edit2.Value = ''
    self.edit2.Refresh()

    self.edit3.Value = ''
    self.edit3.Refresh()

    self.edit4.Value = ''
    self.edit4.Refresh()

    self.edit5.Value = ''
    self.edit5.Refresh()

    self.edit6.Value = ''
    self.edit6.Refresh()

    self.edit7.Value = ''
    self.edit7.Refresh()

    self.edit8.Value = ''
    self.edit8.Refresh()

    self.edit9.Value = ''
    self.edit9.Refresh()

    self.edit10.Value = ''
    self.edit10.Refresh()

    self.edit11.Value = ''
    self.edit11.Refresh()

    self.edit12.Value = ''
    self.edit12.Refresh()

    self.edit13.Value = ''
    self.edit13.Refresh()

    self.edit14.Value = ''
    self.edit14.Refresh()

    self.edit15.Value = ''
    self.edit15.Refresh()

    self.edit16.Value = ''
    self.edit16.Refresh()

    self.edit17.Value = ''
    self.edit17.Refresh()

    self.edit18.Value = ''
    self.edit18.Refresh()

    self.edit19.Value = ''
    self.edit19.Refresh()

    self.edit20.Value = '*'
    self.edit20.Refresh()



class Create_MSAG_SO_Dialog(wx.Dialog):

    def __init__(self, parent, id=-1, title="MSAG SOI Data"):
        wx.Dialog.__init__(self, parent, id, title, size=(730, 400))
        
        self.SetBackgroundColour((255,228,196))  # bisque    
        
        # for display common messages on this dialog
        julianday = SO_utils.get_julianday()

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(285, 260), size=wx.Size(185, 20))
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Today's Julian date is   %s\n" % julianday)

        ### Display_single_MSAG_record(self)
        # Get default values for new ALI record
        retvars = default_MSAG_fields_for_new_record()
        PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,XCH,general,TAR,FOC,reserved,EExDate,EOR = retvars
        Display_single_MSAG_record_with_data(self, PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,     \
                                               XCH,general,TAR,FOC,reserved,EExDate,EOR)
        
        self.button1 = wx.Button(self, wx.ID_OK, label="ADD current record to data file",
            pos=wx.Point(180, 300), size=wx.Size(185, 28))
        prompt = "ADD current record to MSAG SOI data file"
        self.button1.SetToolTip(wx.ToolTip(prompt)) 
        self.button1.SetBackgroundColour((217,255,219)) # vegaseat green

        self.button2 = wx.Button(self, wx.ID_CANCEL, label="Cancel",
            pos=wx.Point(420, 300), size=wx.Size(140, 28))
        prompt = "Cancel saving modified MSAG SO dat file"
        self.button2.SetToolTip(wx.ToolTip(prompt)) 
        self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
        # enter to tab, move to next field
        return_id = wx.NewId()
        acc_table = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, return_id)])
        self.SetAcceleratorTable(acc_table)
        wx.EVT_MENU(self, return_id, self.on_return)


        # respond to button click event
        self.button1.Bind(wx.EVT_BUTTON, self.button1Click, self.button1)

        # respond to button click event
        self.button2.Bind(wx.EVT_BUTTON, self.onCancel, self.button2)
        
       
    def button1Click(self,event):
        """SAVE modified ALI SO DAT file button has been clicked"""

        try:
            # string of record to build
            lineout = []

            MSAGfields = Define_MSAG_fields(self)

            PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,XCH,general,TAR,FOC,reserved,EExDate,EOR = MSAGfields
            
            # building the record
            lineout = PrDir + streetname + StSffx + PoDir + Low + High + MSAGcomm +  \
                      ST + oddeven + ESN + ExDate + PSAPid + COID + XCH + general +  \
                      TAR + FOC + reserved + EExDate + EOR

            try:
                # write current record to temp MSAG SOI data file
                with open(MSAGpath,"a") as M_datfile:
                    M_datfile.write(str(lineout) + '\n')

                SO_utils.MsgBox("Current record has been added to file\n   %s" % M_datfile,"Current record has been added to file")
            except:
                print "Exception in writing MSAG record to  %s\n" % M_datfile

            #Refresh_MSAG_self_edit(self)

            # Get default values for new ALI record
            retvars = default_MSAG_fields_for_new_record()
            PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,XCH,general,TAR,FOC,reserved,EExDate,EOR = retvars
            Display_single_MSAG_record_with_data(self, PrDir,streetname,StSffx,PoDir,Low,High,MSAGcomm,ST,oddeven,ESN,ExDate,PSAPid,COID,     \
                                                   XCH,general,TAR,FOC,reserved,EExDate,EOR)

        except:
            print "Exception button1click - Create_MSAG_SO_Dialog"
            self.Destroy()


    def onCancel(self, event):
        # close M_datfile  No need since using  with open()
        #M_datfile.close()

        self.result = None
        self.Destroy()
        
    def on_return(self, event):
        """
        Enter to tab, move to next field
        """
        ctl = wx.Window_FindFocus()
        ctl.Navigate()

       
def waiting_for_file(path, timeout):
    global check
    check = 0
                  
    observer = Observer()
    observer.schedule(MyPatternMatchingHandler(), path)
    
    observer.start()

    print check
    print timeout
    print path
    
    while ((check == 0) and (timeout > 0)):
        time.sleep(1)
        timeout = timeout - 1
        print timeout

        # display busy dialog
        message = "Please wait..."
        busy = PBI.PyBusyInfo(message, parent=None, title="Processing",)
        wx.Yield()        
        for indx in xrange(timeout):
            wx.MilliSleep(10)
        del busy

    observer.stop()
    observer.join()


class Disclaimer(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="Disclaimer")
        
        disclaimer_text = _msg1
        
        text = wx.TextCtrl(self, -1, disclaimer_text, size=(320,240), style=wx.TE_MULTILINE | wx.TE_READONLY)
        text1 = wx.TextCtrl(self, -1, disclaimer_text, size=(320,240), style=wx.TE_MULTILINE | wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL )
        
        btnsizer = wx.BoxSizer()

        btn = wx.Button(self, wx.ID_OK)
        btnsizer.Add(btn, 0, wx.ALL, 5)
        btnsizer.Add((5,-1), 0, wx.ALL, 5)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.Add(btn, 0, wx.ALL, 5)

        sizer.Add(text, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(text1, 0, wx.EXPAND|wx.ALL, 5)
        
        sizer.Add(btnsizer, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)    
        self.SetSizerAndFit (sizer)



class CFGDialog_MSAG(wx.Dialog):
    
    JULIANDAY = 0
    
    def __init__(self, parent, id=-1, title="Parameters for MSAG SO CFG file"):
        wx.Dialog.__init__(self, parent, id, title, size=(620, 520))
        
        self.SetBackgroundColour((255,228,196))  # bisque
        
        self.label1 = wx.StaticText(self, -1,
                                    label="Verify previous entered value by pressing <Shift><TAB>\n\r",
                                    pos=wx.Point(150, 20))
        self.label2 = wx.StaticText(self, -1,
                                    label="Re-enter if it's greyed-out due to its invalid value\n\r",
                                    pos=wx.Point(150, 40))
        
        self.label1.SetForegroundColour((38,210,189))      # 255,255,255 = white
        self.label2.SetForegroundColour((38,210,189))      # 217,255,219 = vegaseat green, 192,192,192 = gray

        # for display common messages on this dialog
        julianday = SO_utils.get_julianday()
        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(165, 370), size=wx.Size(185, 20))
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Today's Julian date is   %s\n" % julianday)
        
        wx.StaticText(self, -1, "Enter MSAG cfg file name:", pos=wx.Point(15, 70))
        defaultMSAGcfgfilename = SO_utils.make_default_MSAG_cfg_filename()
        self.edit1 = wx.TextCtrl(self, -1, value=defaultMSAGcfgfilename, pos=wx.Point(15, 90), size=wx.Size(145, 20))
        self.edit1.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit1.SetToolTip(wx.ToolTip("Valid MSAG cfg file name:\n<M_><today's Julian date = %s><3 digit SeqNumber><_UserName>.cfg\nClick MSAG CFG button for the list of available MSAG CFG files\n" % julianday))

        wx.StaticText(self, -1, "Enter MSAG dat file name:", pos=wx.Point(210, 70))
        defaultMSAGdatfilename = SO_utils.make_default_MSAG_dat_filename()
        self.edit2 = wx.TextCtrl(self, -1, value=defaultMSAGdatfilename, pos=wx.Point(210, 90), size=wx.Size(145, 20))
        self.edit2.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit2.SetMaxLength(15)                    # have to be 11 chrs, with extension .dat       
        prompt = "Valid MSAG dat file name:\n<DMSAG><today's Julian date = %s><3 digit SeqNumber>.dat\nClick MSAG DAT button for the list of available MSAG DAT files\n" % julianday
        self.edit2.SetToolTip(wx.ToolTip(prompt))


        #wx.StaticText(self, -1, "Enter provider's parent drive:", pos=wx.Point(415, 70))
        #self.edit3 = wx.TextCtrl(self, -1, value="C:", pos=wx.Point(415, 90), size=wx.Size(145, 20))
        #self.edit3.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit3.SetMaxLength(2)
        #self.edit3.SetToolTip(wx.ToolTip("Valid parent drive is in format <Uppercase Drive letter><:>"))
        
        #wx.StaticText(self, -1, "Enter provider's parent directory:", pos=wx.Point(15, 130))
        #self.edit4 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 150), size=wx.Size(145, 20))
        #self.edit4.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit4.SetToolTip(wx.ToolTip("Valid parent directory is alphanumeric characters including underscore"))


        wx.StaticText(self, -1, "Enter provider's location:", pos=wx.Point(210, 130))
        self.edit6 = wx.TextCtrl(self, -1, value='', pos=wx.Point(210, 150), size=wx.Size(145, 20))
        self.edit6.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit6.SetToolTip(wx.ToolTip("Valid provider's location is alphanumeric characters"))

        wx.StaticText(self, -1, "Enter User Name for MSAG:", pos=wx.Point(415, 130))
        self.edit5 = wx.TextCtrl(self, -1, value="", pos=wx.Point(415, 150), size=wx.Size(145, 20))
        self.edit5.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit5.SetMaxLength(15)
        self.edit5.SetToolTip(wx.ToolTip("Valid UserName is alphanumeric characters  max. 15 characters\nClick MSAG User Name button for the list of available MSAG user names\n"))


        wx.StaticText(self, -1, "Enter count of processed:", pos=wx.Point(15, 190))
        self.edit7 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(15, 210), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit7.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit7.SetToolTip(wx.ToolTip("Valid count of processed records is numeric"))

        wx.StaticText(self, -1, "Enter count of errors records:", pos=wx.Point(210, 190))
        self.edit9 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 210), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit9.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit9.SetToolTip(wx.ToolTip("Valid count of error records is numeric"))

        wx.StaticText(self, -1, "Enter count of inserts records:", pos=wx.Point(415, 190))
        self.edit10 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(415, 210), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit10.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit10.SetToolTip(wx.ToolTip("Valid count of inserts records is numeric"))

        wx.StaticText(self, -1, "Enter count of deletes records:", pos=wx.Point(15, 250))
        self.edit11 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(15, 270), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit11.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit11.SetToolTip(wx.ToolTip("Valid count of deletes records is numeric"))

        wx.StaticText(self, -1, "Enter count of befores records:", pos=wx.Point(210, 250))
        self.edit12 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 270), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit12.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit12.SetToolTip(wx.ToolTip("Valid count of befores records is numeric"))

        wx.StaticText(self, -1, "Enter count of afters records:", pos=wx.Point(415, 250))
        self.edit13 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(415, 270), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit13.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit13.SetToolTip(wx.ToolTip("Valid count of afters records is numeric"))

        wx.StaticText(self, -1, "Enter count of nonprocessed:", pos=wx.Point(15, 310))
        self.edit14 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(15, 330), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit14.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit14.SetToolTip(wx.ToolTip("Valid count of non-processed records is numeric"))

        wx.StaticText(self, -1, "Enter expected processing error:", pos=wx.Point(210, 310))
        self.edit15 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 330), size=wx.Size(145, 20))
        self.edit15.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit15.SetToolTip(wx.ToolTip("Valid processing error is alphanumeric"))

        wx.StaticText(self, -1, "Enter max timeout:", pos=wx.Point(415, 310))
        self.edit16 = wx.TextCtrl(self, -1, value="120", pos=wx.Point(415, 330), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit16.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit16.SetToolTip(wx.ToolTip("Valid max timeout is numeric"))

##        wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(15, 430))
##        self.edit19 = wx.TextCtrl(self, -1, value="", pos=wx.Point(15, 450), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
##        self.edit19.SetBackgroundColour((255,255,197))  # suds yellow
##        self.edit19.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))
##
##        wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(210, 430))
##        self.edit20 = wx.TextCtrl(self, -1, value="", pos=wx.Point(210, 450), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
##        self.edit20.SetBackgroundColour((255,255,197))  # suds yellow
##        self.edit20.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))
##
##        wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(415, 430))
##        self.edit21 = wx.TextCtrl(self, -1, value="", pos=wx.Point(415, 450), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
##        self.edit21.SetBackgroundColour((255,255,197))  # suds yellow
##        self.edit21.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))
        
##        self.button1 = wx.Button(self, -1, label="Create CFG",
##            pos=wx.Point(165, 500), size=wx.Size(100, 28))
##        self.button1.SetBackgroundColour((217,255,219)) # vegaseat green
##
##        self.button2 = wx.Button(self, -1, label="Cancel",
##            pos=wx.Point(345, 500), size=wx.Size(100, 28))
##        self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
        self.button1 = wx.Button(self, wx.ID_OK, label="Create MSAG CFG",
            pos=wx.Point(165, 420), size=wx.Size(130, 28))
        prompt = "Create MSAG CFG file"
        self.button1.SetToolTip(wx.ToolTip(prompt)) 
        self.button1.SetBackgroundColour((217,255,219)) # vegaseat green

        self.button2 = wx.Button(self, wx.ID_CANCEL, label="Cancel",
            pos=wx.Point(345, 420), size=wx.Size(100, 28))
        prompt = "Cancel creating MSAG CFG file"
        self.button2.SetToolTip(wx.ToolTip(prompt)) 
        self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
        # respond to button click event
        self.button1.Bind(wx.EVT_BUTTON, self.button1Click, self.button1)

        # respond to button click event
        self.button2.Bind(wx.EVT_BUTTON, self.onCancel, self.button2)        

        ## Select CFG files button
        #cfg_btn = wx.Button(self, -1, label="..", pos=wx.Point(165, 90), size=wx.Size(20, 20))                         
        #self.Bind(wx.EVT_BUTTON, self.OnCFGButton, cfg_btn)

        # Select DAT files button
        dat_btn = wx.Button(self, -1, label="..", pos=wx.Point(360, 90), size=wx.Size(20, 20))                                           
        self.Bind(wx.EVT_BUTTON, self.OnDATButton, dat_btn)

        # Select UserName button
        UserName_btn = wx.Button(self, -1, label="..", pos=wx.Point(570, 150), size=wx.Size(20, 20))                                                     
        self.Bind(wx.EVT_BUTTON, self.OnUserNameButton, UserName_btn)


        # testing EVT_SET_FOCUS, validate MSAG cfg file name entered
        self.edit1.Bind(wx.EVT_SET_FOCUS, self.on_edit1_got_focus)

        # testing EVT_SET_FOCUS, validate MSAG dat file name entered
        self.edit2.Bind(wx.EVT_SET_FOCUS, self.on_edit2_got_focus)

        ## testing EVT_SET_FOCUS, validate parent drive entered
        #self.edit3.Bind(wx.EVT_SET_FOCUS, self.on_edit3_got_focus)

        ## testing EVT_SET_FOCUS, validate location entered
        self.edit6.Bind(wx.EVT_SET_FOCUS, self.on_edit6_got_focus)


        # testing EVT_SET_FOCUS, validate max-timeout entered
        self.edit16.Bind(wx.EVT_SET_FOCUS, self.on_edit16_got_focus)
        
        # enter to tab, move to next field
        return_id = wx.NewId()
        acc_table = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, return_id)])
        self.SetAcceleratorTable(acc_table)
        wx.EVT_MENU(self, return_id, self.on_return)

        self.result = None        
        self.msagcfg = None
        self.msagdat = None
        #self.parentdrive = None
        self.parentdirectory = None
        self.username = None
        self.location = None
        self.processed = None

        self.nonprocessed = None

        self.errors = None
        self.inserts = None
        self.deletes = None
        self.befores = None
        self.afters = None
        self.maxtimeout = None

        self.e_p_error = None
       
    def button1Click(self,event):
        """Create CFG button has been clicked"""
        self.msagcfg = self.edit1.GetValue()
        self.msagdat = self.edit2.GetValue()

        #self.parentdrive = self.edit3.GetValue()
        self.parentdirectory = prov_parentpath

        self.username = self.edit5.GetValue()
        self.location = self.edit6.GetValue()
        self.processed = self.edit7.GetValue()

        self.nonprocessed = self.edit14.GetValue()

        self.errors = self.edit9.GetValue()
        self.inserts = self.edit10.GetValue()
        self.deletes = self.edit11.GetValue()
        self.befores = self.edit12.GetValue()
        self.afters = self.edit13.GetValue()
        self.e_p_error = self.edit15.GetValue()
        self.maxtimeout = self.edit16.GetValue()
        
        self.Destroy() 

    def onCancel(self, event):
        self.result = None
        self.Destroy()

    def on_return(self, event):
        """
        Enter to tab, move to next field
        """
        ctl = wx.Window_FindFocus()
        ctl.Navigate()


    #def OnCFGButton(self, event):
    #    extension_list = ['cfg','CFG']
    #    prefixed = 'M_'
    #    listCFGfilenames_w_extension = SO_utils.get_filenames_filter_startswith_and_extensions(prefixed, extension_list)

    #    cfgdlg = wx.SingleChoiceDialog( self,
    #                                    "Select a CFG file",
    #                                    "Listing of available CFG files", listCFGfilenames_w_extension, wx.CHOICEDLG_STYLE)
    #    if (cfgdlg.ShowModal() == wx.ID_OK):
    #        self.edit1.Value = cfgdlg.GetStringSelection()
    #        self.cfgfilename = self.edit1.Value
    #        self.edit1.SetBackgroundColour((255,255,255))      #clear the background                

    #    cfgdlg.Destroy

 
    def OnDATButton(self, event):

        #dlg = wx.FileDialog(self, "Select a dat file: ", "", "", "*.DAT", wx.OPEN)
        #if dlg.ShowModal() == wx.ID_OK:
        #    self.filename = dlg.GetFilename()
        #    self.dirname = dlg.GetDirectory()

        #    self.edit2.Value = dlg.GetFilename()
        #    self.datfilename = self.edit2.Value
        #    self.edit2.SetBackgroundColour((255,255,255))      #clear the background
                      
        #dlg.Destroy()

        try:
            extension_list = ['dat','DAT']
            prefixed = 'DMSAG'
            selectedpath_filename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
            selectedpath, selectedfile = selectedpath_filename
            self.edit2.Value = selectedfile
            self.datfilename = self.edit2.Value
            self.edit2.SetBackgroundColour((255,255,255))      #clear the background
        except:
            print "Exception in OnDATButton CFGDialog_MSAG"               


    def OnUserNameButton(self, event):
        """
        "C:\Intrepid_Admin_SO_Files\TUAN\Providers\MSAGSO"
        """
        try:
            if (self.edit6.Value <> ""):
                if os.path.exists(mapdrive + "\\"):
                    path = mapdrive + "\\" + self.edit6.Value + "\\Providers\\MSAGSO\\"
                else: 
                    #path = self.edit3.Value + "\\" + self.edit4.Value + "\\" + self.edit6.Value + "\\Providers\\MSAGSO\\"
                    path = "C:" + "\\" + prov_parentpath + "\\" + self.edit6.Value + "\\Providers\\MSAGSO\\"

                if os.path.exists(path):
                    listCOI = SO_utils.get_ALI_files_and_directories(path)

                    COIdlg = wx.SingleChoiceDialog( self,
                                                    "Select a Company ID",
                                                    "Listing of available Company ID", listCOI, wx.CHOICEDLG_STYLE)
                    if (COIdlg.ShowModal() == wx.ID_OK):
                        self.edit5.Value = COIdlg.GetStringSelection().lstrip('Provider')     # strip 'Provider' from the <Provider><COID> string
                        self.companyID = self.edit5.Value
                        self.edit5.SetBackgroundColour((255,255,255))                         #clear the background                

                    COIdlg.Destroy()
                else:
                    SO_utils.MsgBox("Provider's Location %s does not exist" % self.edit6.Value,"Provider's Location Not Exist")


            else:
                SO_utils.MsgBox("Please enter a non-empty Provider's Location","Invalid Provider's Location")
                print "Invalid Provider's location"


        except:
            print "Exception in OnUserNameButton"

        
    def on_edit1_got_focus(self, evt):
        text_ctrl = self.edit1
        text_ctrl.Value = self.edit1.GetValue()
        
        if  not SO_utils.IsMSAGcfg(text_ctrl.Value):
            #self.label3.SetLabel("Invalid MSAG cfg file   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit1.Value = ''    
            self.edit1.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            #self.label3.SetLabel("")
            self.edit1.Value = text_ctrl.Value
            self.msagcfg = self.edit1.GetValue()
            self.edit1.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit1.Refresh()    
        evt.Skip()

    def on_edit2_got_focus(self, evt):
        text_ctrl = self.edit2
        text_ctrl.Value = self.edit2.GetValue()
        
        if  not SO_utils.IsMSAGdat(text_ctrl.Value):
            #self.label3.SetLabel("Invalid MSAG dat file   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit2.Value = ''    
            self.edit2.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            #self.label3.SetLabel("")
            self.edit2.Value = text_ctrl.Value
            self.msagdat = self.edit2.GetValue()
            self.edit2.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit2.Refresh()    
        evt.Skip()

        
    def on_edit6_got_focus(self, evt):
        text_ctrl = self.edit6
        text_ctrl.Value = self.edit6.GetValue()
        
        if (text_ctrl.Value == ""):
            #self.label3.SetLabel("Invalid provider'slocation   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit6.Value = ''            
            self.edit6.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            self.edit6.Value = text_ctrl.Value
            self.location = self.edit6.GetValue()
            self.edit6.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit6.Refresh()    
        evt.Skip()


    def on_edit16_got_focus(self, evt):
        minimum_required = 120
        text_ctrl = self.edit16
        text_ctrl.Value = self.edit16.GetValue()
        
        if  (int(text_ctrl.Value) < minimum_required):
            #self.label3.SetLabel("Invalid max-timedout   %s\n" % text_ctrl.Value)
            text_ctrl.SetValue(str(minimum_required))
            self.edit16.Value = text_ctrl.Value
            #self.edit7.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            self.edit16.Value = text_ctrl.Value
            self.waittime = self.edit16.GetValue()
            self.edit16.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit16.Refresh()   
        evt.Skip()


    def on_edit5_got_focus(self, evt):
        text_ctrl = self.edit5
        text_ctrl.Value = self.edit5.GetValue()
        
        if  not SO_utils.IsUsername(text_ctrl.Value):
            #self.label3.SetLabel("Invalid Company ID   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit5.Value = ''    
            self.edit5.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            #self.label3.SetLabel("")
            self.edit5.Value = text_ctrl.Value
            self.username = self.edit5.GetValue()
            self.edit5.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit5.Refresh()    
        evt.Skip()



class CFGDialog_ALI(wx.Dialog):

    JULIANDAY = 0

    def __init__(self, parent, id=-1, title="Parameters for ALI SO CFG file"):
        wx.Dialog.__init__(self, parent, id, title, size=(620, 570))
        
        self.SetBackgroundColour((255,228,196))  # bisque
        
        self.label1 = wx.StaticText(self, -1,
                                    label="Verify previous entered value by pressing <Shift><TAB>\n\r",
                                    pos=wx.Point(150, 20))
        self.label2 = wx.StaticText(self, -1,
                                    label="Re-enter if it's greyed-out due to its invalid value\n\r",
                                    pos=wx.Point(150, 40))
        
        self.label1.SetForegroundColour((38,210,189))      # 255,255,255 = white
        self.label2.SetForegroundColour((38,210,189))      # 217,255,219 = vegaseat green, 192,192,192 = gray

        # for display common messages on this dialog
        julianday = SO_utils.get_julianday()

        self.label3 = wx.StaticText(self, -1,
                            label="",
                            pos=wx.Point(165, 440), size=wx.Size(185, 20))
        self.label3.SetForegroundColour((50,30,236))       # 225,40,82 = red
        self.label3.SetLabel("Today's Julian date is   %s\n" % julianday)

        wx.StaticText(self, -1, "Enter ALI CFG file name:", pos=wx.Point(15, 70))
        defaultcfgfilename = SO_utils.make_default_ALI_cfg_filename()
        self.edit1 = wx.TextCtrl(self, -1, value=defaultcfgfilename, pos=wx.Point(15, 90), size=wx.Size(145, 20))
        self.edit1.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit1.SetToolTip(wx.ToolTip("Valid ALI CFG file name:\n<A_><today's Julian date = %s><3 digit SeqNumber><_companyID>.cfg\nClick CFG button for the list of available CFG files\n" % julianday))


        wx.StaticText(self, -1, "Enter DAT file name:", pos=wx.Point(210, 70))
        defaultdatfilename = SO_utils.make_default_ALI_dat_filename()
        self.edit2 = wx.TextCtrl(self, -1, value=defaultdatfilename, pos=wx.Point(210, 90), size=wx.Size(145, 20))
        self.edit2.SetBackgroundColour((255,255,197))  # suds yellow       
        prompt = "Valid ALI DAT file name:\n<today's Julian date = %s><3 digit SeqNumber>.dat\nClick DAT button for the list of available DAT files\n" % julianday
        self.edit2.SetToolTip(wx.ToolTip(prompt))


        #wx.StaticText(self, -1, "Enter provider's parent drive:", pos=wx.Point(415, 70))
        #self.edit3 = wx.TextCtrl(self, -1, value="C:", pos=wx.Point(415, 90), size=wx.Size(145, 20))
        #self.edit3.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit3.SetMaxLength(2)
        #self.edit3.SetToolTip(wx.ToolTip("Valid parent drive is in format <Uppercase Drive letter><:>"))
        
        #wx.StaticText(self, -1, "Enter provider's parent directory:", pos=wx.Point(15, 130))
        #self.edit4 = wx.TextCtrl(self, -1, value='', pos=wx.Point(15, 150), size=wx.Size(145, 20))
        #self.edit4.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit4.SetToolTip(wx.ToolTip("Valid parent directory is alphanumeric characters including underscore"))


        #wx.StaticText(self, -1, "Enter Company ID:", pos=wx.Point(210, 130))
        #self.edit5 = wx.TextCtrl(self, -1, value="", pos=wx.Point(210, 150), size=wx.Size(145, 20))
        #self.edit5.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit5.SetMaxLength(15)
        #self.edit5.SetToolTip(wx.ToolTip("Valid Company ID is alphanumeric characters max. 15 characters\nClick Company ID button for the list of available Company IDs\n"))

        #wx.StaticText(self, -1, "Enter provider's location:", pos=wx.Point(415, 130))
        #self.edit6 = wx.TextCtrl(self, -1, value='', pos=wx.Point(415, 150), size=wx.Size(145, 20))
        #self.edit6.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit6.SetToolTip(wx.ToolTip("Valid provider's location is alphanumeric characters"))


        wx.StaticText(self, -1, "Enter provider's location:", pos=wx.Point(210, 130))
        self.edit6 = wx.TextCtrl(self, -1, value='', pos=wx.Point(210, 150), size=wx.Size(145, 20))
        self.edit6.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit6.SetToolTip(wx.ToolTip("Valid provider's location is alphanumeric characters"))


        wx.StaticText(self, -1, "Enter Company ID:", pos=wx.Point(415, 130))
        self.edit5 = wx.TextCtrl(self, -1, value="", pos=wx.Point(415, 150), size=wx.Size(145, 20))
        self.edit5.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit5.SetMaxLength(15)
        self.edit5.SetToolTip(wx.ToolTip("Valid Company ID is alphanumeric characters max. 15 characters\nClick Company ID button for the list of available Company IDs\n"))

        
        wx.StaticText(self, -1, "Enter max time-out:", pos=wx.Point(15, 190))
        self.edit7 = wx.TextCtrl(self, -1, value="120", pos=wx.Point(15, 210), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit7.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit7.SetToolTip(wx.ToolTip("Valid wait time is numeric (in seconds)"))
        
        wx.StaticText(self, -1, "Enter count of error records:", pos=wx.Point(210, 190))
        self.edit8 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 210), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit8.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit8.SetToolTip(wx.ToolTip("Valid count of error records is numeric"))
        
        wx.StaticText(self, -1, "Enter count of processed records:", pos=wx.Point(415, 190))
        self.edit9 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(415, 210), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit9.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit9.SetToolTip(wx.ToolTip("Valid count of processed records is numeric"))
        
        wx.StaticText(self, -1, "Enter count of insert records:", pos=wx.Point(15, 250))
        self.edit10 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(15, 270), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit10.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit10.SetToolTip(wx.ToolTip("Valid count of insert records is numeric"))
        
        wx.StaticText(self, -1, "Enter count of delete records:", pos=wx.Point(210, 250))
        self.edit11 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 270), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit11.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit11.SetToolTip(wx.ToolTip("Valid count of delete records is numeric"))
        
        wx.StaticText(self, -1, "Enter count of autocorrect records:", pos=wx.Point(415, 250))
        self.edit12 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(415, 270), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit12.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit12.SetToolTip(wx.ToolTip("Valid count of autocorrect records is numeric"))
        
        wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(15, 310))
        self.edit13 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(15, 330), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit13.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit13.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))
        
        wx.StaticText(self, -1, "Enter count of migrate records:", pos=wx.Point(210, 310))
        self.edit14 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 330), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit14.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit14.SetToolTip(wx.ToolTip("Valid count of migrate records is numeric"))

        wx.StaticText(self, -1, "Enter count of unlock records:", pos=wx.Point(415, 310))
        self.edit15 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(415, 330), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit15.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit15.SetToolTip(wx.ToolTip("Valid count of unlock records is numeric"))

        wx.StaticText(self, -1, "Enter count of pilot deletes:", pos=wx.Point(15, 370))
        self.edit16 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(15, 390), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        self.edit16.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit16.SetToolTip(wx.ToolTip("Valid count of pilot deletes records is numeric"))

        wx.StaticText(self, -1, "Enter expected processing error:", pos=wx.Point(210, 370))
        self.edit17 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(210, 390), size=wx.Size(145, 20))
        self.edit17.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit17.SetToolTip(wx.ToolTip("Valid expected processing error is in full description or empty"))

        wx.StaticText(self, -1, "Enter expected queue error:", pos=wx.Point(415, 370))
        self.edit18 = wx.TextCtrl(self, -1, value="0", pos=wx.Point(415, 390), size=wx.Size(145, 20))
        self.edit18.SetBackgroundColour((255,255,197))  # suds yellow
        self.edit18.SetToolTip(wx.ToolTip("Valid expected queue error is in full description or empty"))


        #wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(15, 430))
        #self.edit19 = wx.TextCtrl(self, -1, value="", pos=wx.Point(15, 450), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
        #self.edit19.SetBackgroundColour((255,255,197))  # suds yellow
        #self.edit19.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))

##        wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(210, 430))
##        self.edit20 = wx.TextCtrl(self, -1, value="", pos=wx.Point(210, 450), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
##        self.edit20.SetBackgroundColour((255,255,197))  # suds yellow
##        self.edit20.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))
##
##        wx.StaticText(self, -1, "Enter count of change records:", pos=wx.Point(415, 430))
##        self.edit21 = wx.TextCtrl(self, -1, value="", pos=wx.Point(415, 450), size=wx.Size(145, 20), validator=SO_utils.CharValidator('no-alpha'))
##        self.edit21.SetBackgroundColour((255,255,197))  # suds yellow
##        self.edit21.SetToolTip(wx.ToolTip("Valid count of change records is numeric"))

        
##        self.button1 = wx.Button(self, -1, label="Create CFG",
##            pos=wx.Point(165, 500), size=wx.Size(100, 28))
##        self.button1.SetBackgroundColour((217,255,219)) # vegaseat green
##
##        self.button2 = wx.Button(self, -1, label="Cancel",
##            pos=wx.Point(345, 500), size=wx.Size(100, 28))
##        self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        
        self.button1 = wx.Button(self, wx.ID_OK, label="Create CFG",
            pos=wx.Point(165, 500), size=wx.Size(100, 28))
        prompt = "Create CFG file"
        self.button1.SetToolTip(wx.ToolTip(prompt)) 
        self.button1.SetBackgroundColour((217,255,219)) # vegaseat green

        self.button2 = wx.Button(self, wx.ID_CANCEL, label="Cancel",
            pos=wx.Point(345, 500), size=wx.Size(100, 28))
        prompt = "Cancel creating CFG file"
        self.button2.SetToolTip(wx.ToolTip(prompt)) 
        self.button2.SetBackgroundColour((217,255,219)) # vegaseat green

        ## Select CFG files button
        #cfg_btn = wx.Button(self, -1, label="..", pos=wx.Point(165, 90), size=wx.Size(20, 20))
        ##prompt = "List of available CFG files"
        ##self.cfg_btn.SetToolTip(wx.ToolTip(prompt))                           
        #self.Bind(wx.EVT_BUTTON, self.OnCFGButton, cfg_btn)

        # Select DAT files button
        dat_btn = wx.Button(self, -1, label="..", pos=wx.Point(360, 90), size=wx.Size(20, 20))
        #prompt = "List of available DAT files"
        #self.dat_btn.SetToolTip(wx.ToolTip(prompt))                                    
        self.Bind(wx.EVT_BUTTON, self.OnDATButton, dat_btn)

        # Select Company ID button
        COI_btn = wx.Button(self, -1, label="..", pos=wx.Point(570, 150), size=wx.Size(20, 20))
        #prompt = "List of available Company ID"
        #self.COI_btn.SetToolTip(wx.ToolTip(prompt))                                  
        self.Bind(wx.EVT_BUTTON, self.OnCOIButton, COI_btn)



############# TESTING ##################
        ## calendar date picker
        #input_format = '%d-%m-%Y'
        ##display_format = '%a %d %b %Y'
        #display_format = '%m/%d/%Y'

        #wx.StaticText(self, -1, 'Select Date', pos=(347, 432))
        #self.d = SO_utils.DateCtrl(self, size=wx.Size(130, -1), pos=wx.Point(347, 452),
        #    input_format=input_format, display_format=display_format,
        #    title='Select date', default_to_today=False, allow_null=False)
        
        #self.first_time = True  # don't validate date first time
        #self.SetFocus()


########################################
        #self.dpc = wx.DatePickerCtrl(self, pos=wx.Point(590, 395), size=wx.Size(120,-1), id = ID_DATE,
        #                        style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        #self.dpc.Bind(wx.EVT_DATE_CHANGED,self.OnDateChanged)
        
                
        #self.label4 = wx.StaticText(self, -1,
        #                    label="",
        #                    pos=wx.Point(450, 400), size=wx.Size(120, 20))
        #self.label4.SetForegroundColour((50,30,236))       # 225,40,82 = red

############

    # method defined in class CFGDialog_ALI
    #def OnDateChanged(self,event):
    #    selecteddate = str(self.dpc.GetValue())
    #    seldate = selecteddate[0:9]        
    #    self.label4.SetLabel("Selected date:  %s\n" % seldate)

########################################

        
        # respond to button click event
        self.button1.Bind(wx.EVT_BUTTON, self.button1Click, self.button1)

        # respond to button click event
        self.button2.Bind(wx.EVT_BUTTON, self.onCancel, self.button2)        

        # testing EVT_SET_FOCUS, validate cfg file name entered
        self.edit1.Bind(wx.EVT_SET_FOCUS, self.on_edit1_got_focus)

        # testing EVT_SET_FOCUS, validate dat file name entered
        self.edit2.Bind(wx.EVT_SET_FOCUS, self.on_edit2_got_focus)

        ## testing EVT_SET_FOCUS, validate parent drive entered
        #self.edit3.Bind(wx.EVT_SET_FOCUS, self.on_edit3_got_focus)

        # testing EVT_SET_FOCUS, validate company ID entered
        self.edit5.Bind(wx.EVT_SET_FOCUS, self.on_edit5_got_focus)

        # testing EVT_SET_FOCUS, validate provider's location entered
        self.edit6.Bind(wx.EVT_SET_FOCUS, self.on_edit6_got_focus)

        # testing EVT_SET_FOCUS, validate max-time out
        self.edit7.Bind(wx.EVT_SET_FOCUS, self.on_edit7_got_focus)
        
        # enter to tab, move to next field
        return_id = wx.NewId()
        acc_table = wx.AcceleratorTable([(wx.ACCEL_NORMAL, wx.WXK_RETURN, return_id)])
        self.SetAcceleratorTable(acc_table)
        wx.EVT_MENU(self, return_id, self.on_return)

        self.result = None        
        self.cfgfilename = None
        self.datfilename = None
        #self.parentDrive = None
        self.parentDirectory = None
        self.companyID = None
        self.location = None
        self.waittime = None

        self.inserts = None
        self.processed = None
        self.error = None
        self.delete = None
        self.changes = None
        self.autocorr = None
        self.processerror = None
        self.migrate = None
        self.unlocks = None
        self.pilotdeletes = None
        self.queueerror = None

        ##TESTING
        #self.selectdate = None


    #def OnDateChanged(self,event):
    #    selecteddate = str(self.dpc.GetValue())
    #    seldate = selecteddate[0:9]        
    #    self.label4.SetLabel("Selected date:  %s\n" % seldate)

       
    def button1Click(self,event):
        """Create CFG button has been clicked"""
        self.cfgfilename = self.edit1.GetValue()
        self.datfilename = self.edit2.GetValue()

        #self.parentDrive = self.edit3.GetValue()

        self.parentDirectory = prov_parentpath

        self.companyID = self.edit5.GetValue()
        self.location = self.edit6.GetValue()
        self.waittime = self.edit7.GetValue()

        self.inserts = self.edit10.GetValue()
        self.processed = self.edit9.GetValue()
        self.error = self.edit8.GetValue()
        self.delete = self.edit11.GetValue()
        self.changes = self.edit13.GetValue()
        self.autocorr = self.edit12.GetValue()                
        self.migrate = self.edit14.GetValue()
        self.unlock = self.edit15.GetValue()
        self.pilotdeletes = self.edit16.GetValue()
        self.processerror = self.edit17.GetValue()
        self.queueerror = self.edit18.GetValue()

        ##TESTING
        #self.selectdate = self.d.GetValue()
        
        self.Destroy() 

    def onCancel(self, event):
        self.result = None
        self.Destroy()
        
    def on_return(self, event):
        """
        Enter to tab, move to next field
        """
        ctl = wx.Window_FindFocus()
        ctl.Navigate()


    #def OnCFGButton(self, event):                                
    #    extension_list = ['cfg','CFG']
    #    prefixed = 'A_'
    #    listCFGfilenames_w_extension = SO_utils.get_filenames_filter_startswith_and_extensions(prefixed, extension_list)

    #    cfgdlg = wx.SingleChoiceDialog( self,
    #                                    "Select a CFG file",
    #                                    "Listing of available CFG files", listCFGfilenames_w_extension, wx.CHOICEDLG_STYLE)
    #    if (cfgdlg.ShowModal() == wx.ID_OK):
    #        self.edit1.Value = cfgdlg.GetStringSelection()
    #        self.cfgfilename = self.edit1.Value
    #        self.edit1.SetBackgroundColour((255,255,255))      #clear the background                

    #    cfgdlg.Destroy()

 
    def OnDATButton(self, event):

        #dlg = wx.FileDialog(self, "Select a dat file: ", "", "", "*.DAT", wx.OPEN)
        #if dlg.ShowModal() == wx.ID_OK:
        #    self.filename = dlg.GetFilename()
        #    self.dirname = dlg.GetDirectory()

        #    self.edit2.Value = dlg.GetFilename()
        #    self.datfilename = self.edit2.Value
        #    self.edit2.SetBackgroundColour((255,255,255))      #clear the background                     
        #dlg.Destroy()

        try:
            extension_list = ['dat','DAT']
            prefixed = ''
            selectedpath_filename = SO_utils.select_single_file_with_prefix_and_extension(prefixed, extension_list)
            selectedpath, selectedfile = selectedpath_filename

            self.edit2.Value = selectedfile
            self.datfilename = self.edit2.Value
            self.edit2.SetBackgroundColour((255,255,255))      #clear the background
        except:
            print "Cancel was pressed in OnDATButton CFGDialog_ALI"               


    def OnCOIButton(self, event):
        """
        "C:\Intrepid_Admin_SO_Files\TUAN\Providers"
        MSAG  dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
        """
        #path = self.edit3.Value + "\\" + self.edit4.Value + "\\" + self.edit6.Value + "\\Providers\\"
        
        try:
            if (self.edit6.Value <> ""):
                if os.path.exists(mapdrive + "\\"):
                    path = mapdrive + "\\" + self.edit6.Value + "\\Providers\\"
                else: 
                    #path = self.edit3.Value + "\\" + self.edit4.Value + "\\" + self.edit6.Value + "\\Providers\\"
                    path = "C:" + "\\" + prov_parentpath + "\\" + self.edit6.Value + "\\Providers\\"

                if os.path.exists(path):
                    listCOI = SO_utils.get_ALI_files_and_directories(path)

                    COIdlg = wx.SingleChoiceDialog( self,
                                                    "Select a Company ID",
                                                    "Listing of available Company ID", listCOI, wx.CHOICEDLG_STYLE)
                    if (COIdlg.ShowModal() == wx.ID_OK):
                        self.edit5.Value = COIdlg.GetStringSelection().lstrip('Provider')     # strip 'Provider' from the <Provider><COID> string
                        self.companyID = self.edit5.Value
                        self.edit5.SetBackgroundColour((255,255,255))                         #clear the background                

                    COIdlg.Destroy()
                else:
                    SO_utils.MsgBox("Provider's Location %s does not exist" % self.edit6.Value,"Provider's Location Not Exist")

            else:
                SO_utils.MsgBox("Please enter a non-empty Provider's Location","Invalid Provider's Location")
                print "Invalid Provider's location"

        except:
            print "Cancel was pressed in OnCOI CFGDialog_ALI"
 
                  
    def on_edit1_got_focus(self, evt):
        text_ctrl = self.edit1
        text_ctrl.Value = self.edit1.GetValue()
                
        if not SO_utils.IsALIcfg(text_ctrl.Value):
            #self.label3.SetLabel("Invalid CFG file   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit1.Value = ''            
            self.edit1.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            self.edit1.Value = text_ctrl.Value
            self.cfgfilename = self.edit1.GetValue()
            self.edit1.SetBackgroundColour((255,255,255))      #clear the background

        self.edit1.Refresh()  
        evt.Skip()


    #def on_edit2_got_focus(self, evt):
    #    text_ctrl = self.edit2
    #    text_ctrl.Value = self.edit2.GetValue()
        
    #    if not SO_utils.IsValidDatFile(text_ctrl.Value):
    #        #self.label3.SetLabel("Invalid DAT file   %s\n" % text_ctrl.Value)
    #        text_ctrl.Value = ''
    #        self.edit2.Value = ''            
    #        self.edit2.SetBackgroundColour((192,192,192))      #set background to gray                           
    #    else:
    #        # verify DAT file exists
    #        cwdir = os.getcwd()
    #        cwdir += "\\" + text_ctrl.Value

    #        if os.path.exists(cwdir):
    #            self.edit2.Value = text_ctrl.Value
    #            self.datfilename = self.edit2.GetValue()
    #            self.edit2.SetBackgroundColour((255,255,255))      #clear the background
    #        else:
    #            #self.label3.SetLabel(text_ctrl.Value + "  does not exist.")               
    #            self.edit2.Value = ''
    #            text_ctrl.Value = ''       
    #            self.edit2.SetBackgroundColour((192,192,192))      #set background to gray
                 
    #    self.edit2.Refresh()
    #    evt.Skip()


    def on_edit2_got_focus(self, evt):
        text_ctrl = self.edit2
        text_ctrl.Value = self.edit2.GetValue()
        
        if  not SO_utils.IsValidDatFile(text_ctrl.Value):
            #self.label3.SetLabel("Invalid ALI dat file   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit2.Value = ''    
            self.edit2.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            #self.label3.SetLabel("")
            self.edit2.Value = text_ctrl.Value
            self.msagdat = self.edit2.GetValue()
            self.edit2.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit2.Refresh()    
        evt.Skip()
 
          
    #def on_edit3_got_focus(self, evt):
    #    text_ctrl = self.edit3
    #    text_ctrl.Value = self.edit3.GetValue()
        
    #    if not SO_utils.IsValidParentDrive(text_ctrl.Value):
    #        #self.label3.SetLabel("Invalid parent drive   %s\n" % text_ctrl.Value)
    #        text_ctrl.Value = ''
    #        self.edit3.Value = ''            
    #        self.edit3.SetBackgroundColour((192,192,192))      #set background to gray            
    #    else:
    #        self.edit3.Value = text_ctrl.Value
    #        self.parentDrive = self.edit3.GetValue()
    #        self.edit3.SetBackgroundColour((255,255,255))      #clear the background
        
    #    self.edit3.Refresh()  
    #    evt.Skip()


    def on_edit5_got_focus(self, evt):
        text_ctrl = self.edit5
        text_ctrl.Value = self.edit5.GetValue()
        
        if  not SO_utils.IsCompanyID(text_ctrl.Value):
            #self.label3.SetLabel("Invalid Company ID   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit5.Value = ''    
            self.edit5.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            self.edit5.Value = text_ctrl.Value
            self.companyID = self.edit5.GetValue()
            self.edit5.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit5.Refresh()    
        evt.Skip()


    # provider's location
    def on_edit6_got_focus(self, evt):
        text_ctrl = self.edit6
        text_ctrl.Value = self.edit6.GetValue()
        
        if  (self.edit6.Value == ''):
            #self.label3.SetLabel("Invalid provider's location   %s\n" % text_ctrl.Value)
            text_ctrl.Value = ''
            self.edit6.Value = ''    
            self.edit6.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            self.edit6.Value = text_ctrl.Value
            self.location = self.edit6.GetValue()
            self.edit6.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit6.Refresh()    
        evt.Skip()


    def on_edit7_got_focus(self, evt):
        minimum_required = 120
        text_ctrl = self.edit7
        text_ctrl.Value = self.edit7.GetValue()
        
        if  (int(text_ctrl.Value) < minimum_required):
            #self.label3.SetLabel("Invalid max-timedout   %s\n" % text_ctrl.Value)
            text_ctrl.SetValue(str(minimum_required))
            self.edit7.Value = text_ctrl.Value
            #self.edit7.SetBackgroundColour((192,192,192))      #set background to gray            
        else:
            self.edit7.Value = text_ctrl.Value
            self.waittime = self.edit7.GetValue()
            self.edit7.SetBackgroundColour((255,255,255))      #clear the background
        
        self.edit7.Refresh()   
        evt.Skip()



class main_window(wx.Frame):
    
    def __init__(self):
        #wx.Frame.__init__(self, None, -1, '', size=(300, 200))
        self.frame = wx.Frame.__init__(self, None, -1, '', size=(300, 200))

        # define panel
        mypanel = wx.Panel(self.frame, wx.ID_ANY)
                
        # use monospaced font
        txt = wx.TextCtrl(self, -1) 
        font = txt.GetFont() 
        font = wx.Font(font.GetPointSize(), wx.TELETYPE, 
                       font.GetStyle(), 
                       font.GetWeight(), font.GetUnderlined()) 
        txt.SetFont(font)

##        m_text = wx.StaticText(mypanel, -1, "ALI SO Process")
##        m_text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
##        m_text.SetSize(m_text.GetBestSize())
##        mypanel.Add(m_text, 0, wx.ALL, 10)       

    def SetOutput(self, output):
        self.output = output
        
    def OnSelChanged(self, event):
        item =  event.GetItem()
 
                               
    def opendir(self, event):
        """ Open a file"""
        dlg = wx.FileDialog(self, "Choose a file to edit: ", self.dirname, "", "*.CFG", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()

            f = open(os.path.join(self.dirname, self.filename), 'r')

            #show the opened file name on status bar 
            self.SetStatusText("Opened file = %s\n\r" % self.filename)
            self.Refresh()

            self.control.SetValue(f.read())
            f.close()            
        dlg.Destroy()
 
               
    def savedir(self, event):
        """ Save edited file """
        # Save away the edited text        
        dlg = wx.FileDialog(
             self, message="Save file as ...",
             defaultDir=".",
             defaultFile="", wildcard="*.CFG", style=wx.SAVE
             )

        if dlg.ShowModal() == wx.ID_OK:
            # Grab the content to be saved
            itcontains = self.control.GetValue()            
            #output_stream = wx.FileOutputStream(dlg.GetPath())

            # Open the file for write, write, close
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()

            filehandle = open(os.path.join(self.dirname, self.filename),'w')

            filehandle.write(itcontains)
            #filehandle.write(output_stream)

            filehandle.close()

        # Get rid of the dialog to keep things tidy
        dlg.Destroy()

        
    def OnExit(self,e):
        self.Close(True)

        
    def __init__(self, parent, title):
        self.dirname = ''
        self.testcaselog = ''

        wx.Frame.__init__(self, parent, title=title, size=(500, 500),style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
         
        # main frame is a multiline text box
        self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        
        self.SetBackgroundColour((255,228,196))  # bisque
        
        status=self.CreateStatusBar()
                
        menubar=wx.MenuBar()        
        first=wx.Menu()
        second=wx.Menu()
        third=wx.Menu()
        fourth=wx.Menu()
        fifth=wx.Menu()
        sixth=wx.Menu()
        
        menubar.Append(first,"&File")
        menubar.Append(second,"&Create")
        menubar.Append(third,"&Process")
        menubar.Append(fourth,"Show")
        menubar.Append(fifth,"&Reports")
        menubar.Append(sixth,"&About")
         
        first.Append(104,"&Open a file to edit"," Open a file to edit")
        first.Append(101,"&Save edited file"," Save edited file")
        first.Append(105,"&Exit","Quit")
        
        second.Append(102,"Create new &ALI SO CFG file","Create new ALI CFG")
        second.Append(116,"Create new &MSAG SO CFG file","Create new MSAG CFG")
        second.Append(123,"Create new ALI SOI data file","Create new ALI SOI data file")
        second.Append(124,"Create new MSAG SOI data file","Create new MSAG SOI data file")
        second.Append(121,"Edit existing ALI SOI data file","Edit existing ALI SOI data file")
        second.Append(122,"Edit existing MSAG SOI data file","Edit existing MSAG SOI data file")

        third.Append(108,"Process ALI SO","Run one or more ALI SO tests")
        third.Append(112,"Process MSAG SO","Run one or more MSAG SO tests")

        fourth.Append(103,"&Show detail report of last run test case")
        fourth.Append(107,"Show today's &Julian Date")
        fourth.Append(109,"Show ALI SO error codes and descriptions")
        fourth.Append(115,"Show MSAG SO error codes and descriptions")

        #fifth.Append(110,"&Details Report"," Details Report of all test cases")
        fifth.Append(111,"&Summary Report"," Summary Report of all test cases")

        sixth.Append(106,"&About the SO process")
        
        self.SetMenuBar(menubar)
                
        self.Bind(wx.EVT_MENU, self.OnExit, id=105)
        self.Bind(wx.EVT_MENU, self.opendir, id=104)
        self.Bind(wx.EVT_MENU, self.savedir, id=101)
        self.Bind(wx.EVT_MENU, self.create_ali, id=102)
        self.Bind(wx.EVT_MENU, self.create_msag, id=116)
        self.Bind(wx.EVT_MENU, self.edit_ali_dat, id=121)
        self.Bind(wx.EVT_MENU, self.edit_msag_dat, id=122)
        self.Bind(wx.EVT_MENU, self.create_ali_dat, id=123)
        self.Bind(wx.EVT_MENU, self.create_msag_dat, id=124)

                 
        self.Bind(wx.EVT_MENU, self.show, id=103)

        #self.Bind(wx.EVT_MENU, self.about, id=106)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=106)

        self.Bind(wx.EVT_MENU, self.juliandate, id=107)
        self.Bind(wx.EVT_MENU, self.processALI, id=108)
        self.Bind(wx.EVT_MENU, self.processMSAG, id=112)
        self.Bind(wx.EVT_MENU, self.edescription, id=109)
        self.Bind(wx.EVT_MENU, self.msag_edescription, id=115)

        #self.Bind(wx.EVT_MENU, self.detailrpt, id=110)
        self.Bind(wx.EVT_MENU, self.summaryrpt, id=111)

        self.Centre()
        self.Show(True)


    def about(mypanel, event):
        """ About the application """
        #wx.MessageBox(_msg,'About the SO process', wx.STAY_ON_TOP)

        # First we create and fill the info object
        info = wx.AboutDialogInfo()
        #info.Name = "About the ALI SO process"
        #info.Version = "1.0.0"
        #info.Copyright = "2015 PythonCoders"
        info.Description = wordwrap(_msgAbout,650, wx.ClientDC(mypanel))

        #nfo.WebSite = ("http://www.telecomsys.com", "SO Process")
        #info.Developers = [ "Tuan Duc Do" ]

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)        


    def OnAbout(self, event):
        dlg = AboutBox()
        dlg.ShowModal()
        dlg.Destroy()


    def edit_ali_dat(self, event):
        try:
            ## show dialog
            #dlg = Edit_ALI_SO_Dialog(None, wx.ID_ANY, u'Edit ALI SOI data file - %s' % SOI_data_format)
            #dlg.ShowModal()
            #dlg.Destroy()

            # show dialog using ObjectList View - remember to un-comment line 29
            #from ObjectListView import ObjectListView, ColumnDefn     #for ObjectListView     - Cannot py2exe if using ObjectListView
            dlg = Edit_ALI_SO_Dialog_OLV(None, wx.ID_ANY, u'Edit ALI SOI data file - %s' % SOI_data_format)
            dlg.ShowModal()
            dlg.Destroy()

        except:
            print "Cancel was pressed in edit_ali_dat"


    def edit_msag_dat(self, event):
        try:
            ## show dialog
            #dlg = Edit_MSAG_SO_Dialog(None, wx.ID_ANY, u'Edit MSAG SOI data file - %s' % SOI_data_format)
            #dlg.ShowModal()
            #dlg.Destroy()

            # show dialog using Object List View - remember to un-comment on line 29
            #from ObjectListView import ObjectListView, ColumnDefn     #for ObjectListView     - Cannot py2exe if using ObjectListView
            dlg = Edit_MSAG_SO_Dialog_OLV(None, wx.ID_ANY, u'Edit MSAG SOI data file - %s' % SOI_data_format)
            dlg.ShowModal()
            dlg.Destroy()

        except:
            print "Cancel was pressed in edit_msag_dat"


    def create_ali_dat(self, event):
        try:
            # show dialog
            dlg = Create_ALI_SO_Dialog(None, wx.ID_ANY, u'Create new ALI SOI data file - %s' % SOI_data_format)
            dlg.ShowModal()

            dlg.Destroy()
        except:
            print "Cancel was pressed in create_ali_dat"


    def create_msag_dat(self, event):
        try:
            # show dialog
            dlg = Create_MSAG_SO_Dialog(None, wx.ID_ANY, u'Create new MSAG SOI data file - %s' % SOI_data_format)
            dlg.ShowModal()

            dlg.Destroy()

        except:
            print "Cancel was pressed in create_msag_dat"


    def show(self, event):
        """ show last run test case details report """
        if self.testcaselog != '':
            f = open(self.testcaselog, "r")
            msg = f.read()
            f.close()

            dlg = SO_utils.ShowLastRun(self, msg, "Detail report of last run test case:  %s\n\r" % self.testcaselog)
            
            dlg.ShowModal()     
            dlg.Destroy()

            
    def processMSAG(self, event):
        """ process MSAG SO list of tests """
        #instantiate the class
        pr = ProcessSO()

        #build MSAG SO error code dictionary
        mecode = SO_utils.build_msag_ecode()

        # init Config Parser
        Config = ConfigParser.ConfigParser()
        
        # get list of CFG file names
        try:
            extension_list = ['cfg','CFG']
            prefixed = "M_"
            selectedpath_list_listfilename = SO_utils.select_multi_files_with_prefix_and_extension(prefixed, extension_list)
            selectedpath, selectedlist, listcfgfilenames = selectedpath_list_listfilename
        except:
            listcfgfilenames = []
            print "Cancel was pressed"


        if len(listcfgfilenames) > 0:
            
            # summary report of running the list of tests - f4
            rptpath2 = os.getcwd() + "//" + "ReportSummaryListOfTests.log"
            f4 = open(rptpath2, "a")         # open file for appending

            # parse the list into string array of cfg file names
            listcfgnames = ', '.join(listcfgfilenames)

            # list of cfg file names with CFG extension
            list_names_ext = []

            # list of log file based on cfg file names
            log_filenames = []

            # adding extension '.cfg' to these file names
            for x in listcfgfilenames:
                list_names_ext.append(x + '.CFG')

            #write log     
            f4.write("\n\r")    
            f4.write("\n\r")            
            f4.write("============================================================\n\r")    
            f4.write("\n\r")            
            f4.write("SUMMARY REPORT ON LIST OF  %s\n\r" % ', '.join(list_names_ext))
            f4.write("\n\r")
            f4.write("Date: %s" % time.strftime("%x"))
            f4.write("\n\r")
            f4.write("Time: %s" % time.strftime("%X"))
            f4.write("\n\r")    
            f4.write("\n\r")

            # adding log file names based on cfg file names
            for y in listcfgfilenames:
                log_filenames.append(y + '.log')

            logfilepath = os.getcwd() + "\\"

            count = 0
            # starting the loop
            for testcase in list_names_ext:

                self.testcaselog = log_filenames[count]
                f1 = open(logfilepath + self.testcaselog, "w")

                #write log     
                f1.write("TEST REPORT ON %s\n\r" % testcase) 
                f1.write("Date: %s" % time.strftime("%x"))
                f1.write("Time: %s" % time.strftime("%X"))   
                f1.write("\n\r")

                f4.write("TEST REPORT ON %s\n\r" % testcase) 
                f4.write("Date: %s" % time.strftime("%x"))
                f4.write("Time: %s" % time.strftime("%X"))
                f4.write("\n\r")

                #write to status bar
                self.SetStatusText('Running: %s\n' % testcase)
                self.Refresh()

                try:
                    # expected results
                    e_results = []                         # list to keep expected results

                    # use MSAG
                    TestResult = pr.Run_MSAG_test(f1, Config, e_results, testcase, pr, mecode)

                    # write log
                    if TestResult:
                        self.SetStatusText("Test case %s  =  PASS\n\r" % testcase)
                        self.Refresh()

                        f1.write("Test case %s  =  PASS\n\r" % testcase)

                        f4.write("Test case %s  =  PASS\n\r" % testcase)
                        f4.write("\n\r")
                                            
                        # create .PASS test result
                        testcaseresult = os.getcwd() + "\\" + listcfgfilenames[count] + '.PASS'
                    
                        f2 = open(testcaseresult, "w")
                        f2.write("Test case  %s  =  PASS\n\r" % listcfgfilenames[count])

                    else:
                        self.SetStatusText("Test case %s  =  FAIL\n\r" % testcase)
                        self.Refresh()        
                    
                        f1.write("\n\r")
                        f1.write("Test case %s  =  FAIL\n\r" % testcase)

                        f4.write("\n\r")
                        f4.write("Test case %s  =  FAIL\n\r" % testcase)
                                            
                        # create .FAIL test result
                        testcaseresult = os.getcwd() + "\\" + listcfgfilenames[count] + '.FAIL'
                    
                        f2 = open(testcaseresult, "w")
                        f2.write("Test case  %s  =  FAIL\n\r" % listcfgfilenames[count])
                                    
                except:
                    status = 1    # set to 1 on error
               
                    self.SetStatusText("Test case %s  =  FAIL\n\r % testcase")
                    self.Refresh()        

                    #f1.write("Exception - program halts. Exiting.\n\r")
                    f1.write("Test case %s  =  FAIL\n\r" % testcase)
                    f1.write("\n\r")

                    # create .FAIL test result
                    testcaseresult = os.getcwd() + "\\" + listcfgfilenames[count] + '.FAIL'                    
                    f2 = open(testcaseresult, "w")
                    f2.write("Test case  %s  =  FAIL\n\r" % listcfgfilenames[count])
                                          
                    f4.write("Test case %s  =  FAIL\n\r" % testcase)
                    f4.write("\n\r")                                               
               
                self.SetStatusText("------- DONE ------- Running  %s  completed.\n\r" % testcase)
                self.Refresh()       

                # increment the count
                count = count + 1

            # close report running list of tests
            f1.close()
            f2.close()
            f4.close()
        
                      
    def juliandate(self, event):
        """
        Show today's julian date
        """
        julianday = SO_utils.get_julianday()
        prompt = "     Today's julian date is    %s\n\r" % julianday
        title = 'General'
        SO_utils.display_msg(prompt, title)


    def edescription(self, event):
        """
        Show ALI SO error code description providing error code
        """
        try:
            execpath = os.getcwd() + "\\" + "SO_errorcode.exe"
            os.startfile(execpath)
        except:
            print "Exception in edescription"

    def msag_edescription(self, event):
        """
        Show MSAG SO error code description providing error code
        """
        try:
            execpath = os.getcwd() + "\\" + "SO_MSAG_errorcode.exe"
            os.startfile(execpath)
        except:
            print "Exception in msag_edescription"

                       
    def summaryrpt(self, event):
        """ show last run test case details report """
        summaryrpt = "ReportSummaryListOfTests.log"

        try:
            curdir = os.getcwd()
            curpath = curdir + "\\" + summaryrpt
            if  os.path.exists(curpath):
                f = open(summaryrpt, "r")
                msg = f.read()
                f.close()           
                dlg = SO_utils.ShowLastRun(self, msg, "Summary report of all test runs\n\r")
            
                dlg.ShowModal()     
                dlg.Destroy()
            else:
                #self.SetStatusText("%s does not exists in %s\n\r" % (summaryrpt, curdir))
                #self.Refresh()
                print "%s does not exists in %s\n\r" % (summaryrpt, curdir)
                return False
        except:
            #self.SetStatusText("Exception of %s\n\r" % summaryrpt)
            #self.Refresh()
            print "Exception of %s\n\r" % summaryrpt
            return False


    def detailrpt(self, event):
        """ show details report of all test runs"""
        detailrpt = "ReportDetailsListOfTests.log"
        self.SetStatusText("")
        self.Refresh()

        try:
            curdir = os.getcwd()
            curpath = curdir + "\\" + detailrpt
            if os.path.exists(curpath):
                f = open(detailrpt, "r")
                msg = f.read()
                f.close()
                       
                dlg = SO_utils.ShowLastRun(self, msg, "Details report of all test runs\n\r")
            
                dlg.ShowModal()     
                dlg.Destroy()
            else:
                #self.SetStatusText("%s does not exists in %s\n\r" % (detailrpt, curdir))
                #self.Refresh()
                print "%s does not exists in %s\n\r" % (detailrpt, curdir)
                return False
        except:
            #self.SetStatusText("Exception of %s\n\r" % detailrpt)
            #self.Refresh()
            print "Exception of %s\n\r" % detailrpt
            return False 
 
                                       
    def create_ali(self, event):
        """
        Create a new ALI SO CFG file
        """
        try:             
            #dlg = Disclaimer(self)
        
            dlg = CFGDialog_ALI(self)        
            dlg.ShowModal()
                
            cfg_file = dlg.cfgfilename.strip()
            datfile  = dlg.datfilename.strip()
            parentdrive = local_mapdrive.strip()
            parentdir = dlg.parentDirectory.strip()
            companyID = dlg.companyID.strip()
            location = dlg.location.strip()
            waittime = dlg.waittime.strip()
            inserts = int(dlg.inserts.strip())
            processed = int(dlg.processed.strip())
            errors = int(dlg.error.strip())
            changes = int(dlg.changes.strip())
            delete = int(dlg.delete.strip())
            autocorrect = int(dlg.autocorr.strip())
            migrate = int(dlg.migrate.strip())
            unlock = int(dlg.unlock.strip())
            pilotdeletes = int(dlg.pilotdeletes.strip())

            e_p_error = dlg.processerror.strip()
            e_q_error = dlg.queueerror.strip()


            dlg.Destroy()

            # process error codes and its counts
            a_err_code = []    #list of error code and its counts

            var = 0
            count = 1
            while var < int(errors):              
                if int(errors) > 0:
                      errorcode = ''
                      prompt = "Enter error code %s  of  %s error records:  \n\r" % (count, errors)
                      while errorcode == '':
                        errorcode = SO_utils.get_error_code(prompt)
                    
                      errors_errorcode = 0          
                      while errors_errorcode == 0:
                        prompt = "Enter count for  error code  %s : " % errorcode
                        errors_errorcode = SO_utils.get_errors_errorcode(prompt)

                      if errorcode != '':
                          a_err_code.append(errorcode)
                      
                      if errors_errorcode != 0:                            
                          a_err_code.append(int(errors_errorcode))
                                    
                var = var + int(errors_errorcode)
                count = count + 1

                   
            #verify correct entered error codes        
            self.SetStatusText("Error codes and their count = %s\n\r" % a_err_code)
            self.Refresh()

            # process autocorrect error codes and its counts        
            a_autocorr_err_code = []    #list of autocorrect error code and its counts

            var = 0
            count = 1
            while var < int(autocorrect):              
                if int(autocorrect) > 0:
                      autocorr_errorcode = ''
                      prompt = "Enter autocorrect error code  %s of %s  autocorrect records:  \n\r" % (count, autocorrect)
                      while autocorr_errorcode == '':
                        autocorr_errorcode = SO_utils.get_error_code(prompt)
                    
                      autocorr_errors_errorcode = 0          
                      while autocorr_errors_errorcode == 0:
                        prompt = "Enter count for  %s  autocorr error code: " % autocorr_errorcode
                        autocorr_errors_errorcode = SO_utils.get_errors_errorcode(prompt)

                      if autocorr_errorcode != '':
                          a_autocorr_err_code.append(autocorr_errorcode)
                      
                      if autocorr_errors_errorcode != 0:              
                          a_autocorr_err_code.append(int(autocorr_errors_errorcode))
                                    
                var = var + int(autocorr_errors_errorcode)
                count = count + 1


            # process migrate error codes and its counts        
            a_migrate_err_code = []    #list of migrate error code and its counts

            var = 0
            count = 1
            while var < int(migrate):              
                if int(migrate) > 0:
                      migrate_errorcode = ''
                      prompt = "Enter migrate error code  %s  of  %s  migrate records:  \n\r" % (count, migrate)
                      while migrate_errorcode == '':
                        migrate_errorcode = SO_utils.get_error_code(prompt)
                    
                      migrate_errors_errorcode = 0          
                      while migrate_errors_errorcode == 0:
                        prompt = "Enter count for  %s  migrate error code: " % migrate_errorcode
                        migrate_errors_errorcode = SO_utils.get_errors_errorcode(prompt)

                      if migrate_errorcode != '':
                          a_migrate_err_code.append(migrate_errorcode)
                      
                      if migrate_errors_errorcode != 0:              
                          a_migrate_err_code.append(int(migrate_errors_errorcode))
                                    
                var = var + int(migrate_errors_errorcode)
                count = count + 1

                   
            cfgfile = open(cfg_file, 'w')
            Config = ConfigParser.ConfigParser()

            # add the settings to the structure of the file
            Config.add_section('General')
            Config.set('General','datfile', datfile)
            Config.set('General','companyID', companyID)
            Config.set('General','location', location)
            Config.set('General','parentdrive', parentdrive)
            Config.set('General','parentdir',parentdir)
            Config.set('General','waittime', waittime)

            Config.add_section('STA File')
            Config.set('STA File','inserts', int(inserts))
            Config.set('STA File','processed', int(processed))
            Config.set('STA File','errors', int(errors))
            Config.set('STA File','delete', int(delete))
            Config.set('STA File','changes', int(changes))
            Config.set('STA File','autocorrect', int(autocorrect))
            Config.set('STA File','migrate', int(migrate))
            Config.set('STA File','unlock', int(unlock))
            Config.set('STA File','pilotdeletes', int(pilotdeletes))


            Config.add_section('PERR File')
            Config.set('PERR File','process_error', e_p_error)

            Config.add_section('QERR File')
            Config.set('QERR File','queue_error', e_q_error)

            Config.add_section('ERROR Type')
        
            #print out error codes and its counts
            i = 0
            b = len(a_err_code)

            while i < b:
                Config.set('ERROR Type',a_err_code[i], a_err_code[i+1])    
                i = i + 2

            Config.add_section('AUTOCORR')

            #print out autocorrect error codes and its counts
            i = 0
            b = len(a_autocorr_err_code)
            while i < b:    
                Config.set('AUTOCORR',a_autocorr_err_code[i], a_autocorr_err_code[i+1])    
                i = i + 2

            Config.add_section('MERROR Type')

            #print out migrate error codes and its counts
            i = 0
            b = len(a_migrate_err_code)
            while i < b:    
                Config.set('MERROR Type',a_migrate_err_code[i], a_migrate_err_code[i+1])    
                i = i + 2

            ## write to console
            #print "a_err_code = %s\n" % a_err_code
            #print "a_autocorr_err_code = %s\n" % a_autocorr_err_code
            #print "a_migrate_err_code = %s\n" % a_migrate_err_code

            Config.write(cfgfile)
            SO_utils.MsgBox(' Config file  %s  is created.\n\r' % cfg_file,'-------- DONE --------') 

            cfgfile.close()      
            return True
        except:
            print "Cancel was pressed in create_ali"
        

    def create_msag(self, event):
        """
        Create a new MSAG SO CFG file
        """               
        try:
            dlg = CFGDialog_MSAG(self)        
            dlg.ShowModal()
                
            msagcfg = dlg.msagcfg.strip()
            msagdat  = dlg.msagdat.strip()
            parentdrive = local_mapdrive.strip()
            parentdir = dlg.parentdirectory.strip()
            username = dlg.username.strip()
            location = dlg.location.strip()
            inserts = int(dlg.inserts.strip())
            processed = int(dlg.processed.strip())
            errors = int(dlg.errors.strip())

            nonprocessed = int(dlg.nonprocessed.strip())

            deletes = int(dlg.deletes.strip())
            befores = int(dlg.befores.strip())
            afters = int(dlg.afters.strip())
            maxtimeout = int(dlg.maxtimeout.strip())

            e_p_error = dlg.e_p_error.strip()

            dlg.Destroy()

            # process error codes and its counts
            a_err_code = []    #list of error code and its counts

            var = 0
            count = 1
            while var < int(errors):              
                if int(errors) > 0:
                      errorcode = ''
                      prompt = "Enter error code %s  of  %s error records:  \n\r" % (count, errors)
                      while errorcode == '':
                        errorcode = SO_utils.get_msag_error_code(prompt)
                    
                      errors_errorcode = 0          
                      while errors_errorcode == 0:
                        prompt = "Enter count for  error code  %s : " % errorcode
                        errors_errorcode = SO_utils.get_errors_errorcode(prompt)

                      if errorcode != '':
                          a_err_code.append(errorcode)
                      
                      if errors_errorcode != 0:                            
                          a_err_code.append(int(errors_errorcode))
                                    
                var = var + int(errors_errorcode)
                count = count + 1

                   
            #verify correct entered error codes        
            self.SetStatusText("Error codes and their count = %s\n\r" % a_err_code)
            self.Refresh()

                   
            cfgfile = open(msagcfg, 'w')
            Config = ConfigParser.ConfigParser()

            # add the settings to the structure of the file
            Config.add_section('General')
            Config.set('General','msagcfg', msagcfg)
            Config.set('General','username', username)
            Config.set('General','location', location)
            Config.set('General','parentdrive', parentdrive)
            Config.set('General','parentdir',parentdir)
            Config.set('General','msagdat', msagdat)
            Config.set('General','maxtimeout', maxtimeout)          # e_results[6]

            Config.add_section('STA File')
        
            Config.set('STA File','processed', int(processed))

            Config.set('STA File','nonprocessed', int(nonprocessed))

            Config.set('STA File','errors', int(errors))
            Config.set('STA File','inserts', int(inserts))
            Config.set('STA File','deletes', int(deletes))
            Config.set('STA File','befores', int(befores))
            Config.set('STA File','afters', int(afters))


            Config.add_section('PERR File')
            Config.set('PERR File','process_error', e_p_error)

            Config.add_section('ERROR Type')
        
            #print out error codes and its counts
            i = 0
            b = len(a_err_code)

            while i < b:
                Config.set('ERROR Type',a_err_code[i], a_err_code[i+1])    
                i = i + 2


            Config.write(cfgfile)
            SO_utils.MsgBox(' Config file  %s  is created.\n\r' % msagcfg,'-------- DONE --------') 
        
            cfgfile.close()       
            return True

        except:
            print "Cancel was pressed in create_msag"


    def processALI(self, event):
        """
        Run ALI SO list of tests (list of CFG files)
        """              
        #instantiate the class
        pr = ProcessSO()

        #build SO error code dictionary
        ecode = SO_utils.build_ecode()

        # init Config Parser
        Config = ConfigParser.ConfigParser()
        
        # get list of CFG file names 
        try:
            extension_list = ['cfg','CFG']
            prefixed = "A_"
            selectedpath_list_listfilename = SO_utils.select_multi_files_with_prefix_and_extension(prefixed, extension_list)
            selectedpath, selectedlist, listcfgfilenames = selectedpath_list_listfilename
        except:
            listcfgfilenames = []
            print "Cancel was pressed"


        if len(listcfgfilenames) > 0:
            
            # summary report of running the list of tests - f4
            rptpath2 = os.getcwd() + "//" + "ReportSummaryListOfTests.log"
            f4 = open(rptpath2, "a")         # open file for appending

            # parse the list into string array of cfg file names
            listcfgnames = ', '.join(listcfgfilenames)

            # list of cfg file names with CFG extension
            list_names_ext = []

            # list of log file based on cfg file names
            log_filenames = []

            # adding extension '.cfg' to these file names
            for x in listcfgfilenames:
                list_names_ext.append(x + '.CFG')

            #write log 
            f4.write("\n\r")    
            f4.write("\n\r")            
            f4.write("============================================================\n\r")    
            f4.write("\n\r")            
            f4.write("SUMMARY REPORT ON LIST OF  %s\n\r" % ', '.join(list_names_ext))
            f4.write("\n\r")
            f4.write("Date: %s" % time.strftime("%x"))
            f4.write("\n\r")
            f4.write("Time: %s" % time.strftime("%X"))
            f4.write("\n\r")    
            f4.write("\n\r")

            # adding log file names based on cfg file names
            for y in listcfgfilenames:
                log_filenames.append(y + '.log')

            logfilepath = os.getcwd() + "\\"

            count = 0
            # starting the loop
            for testcase in list_names_ext:

                self.testcaselog = log_filenames[count]
                f1 = open(logfilepath + self.testcaselog, "w")

                #write log     
                f1.write("TEST REPORT ON %s\n\r" % testcase) 
                f1.write("\n\r")
                f1.write("Date: %s" % time.strftime("%x"))
                f1.write("Time: %s" % time.strftime("%X"))
                f1.write("\n\r")    

                f4.write("TEST REPORT ON %s\n\r" % testcase) 
                f4.write("\n\r")
                f4.write("Date: %s" % time.strftime("%x"))
                f4.write("Time: %s" % time.strftime("%X"))
                f4.write("\n\r")

                #write to status bar
                self.SetStatusText('Running: %s\n' % testcase)
                self.Refresh()

                try:
                    # expected results - # list to keep expected results
                    e_results = [] 

                    ## dictionaries to hold error code and its count
                    #c_err_code, c_autocorr_err_code, c_migrate_err_code = {}

                    TestResult = pr.Run_test(f1, Config, e_results, testcase, pr, ecode)

                    # write log
                    if TestResult:
                        self.SetStatusText("Test case %s  =  PASS\n\r" % testcase)
                        self.Refresh()

                        f1.write("\n\r")
                        f1.write("Test case %s  =  PASS\n\r" % testcase)

                        f4.write("\n\r")
                        f4.write("Test case %s  =  PASS\n\r" % testcase)
                                            
                        # create .PASS test result
                        testcaseresult = os.getcwd() + "\\" + listcfgfilenames[count] + '.PASS'
                    
                        f2 = open(testcaseresult, "w")
                        f2.write("Test case  %s  =  PASS\n\r" % listcfgfilenames[count])

                    else:
                        self.SetStatusText("Test case %s  =  FAIL\n\r" % testcase)
                        self.Refresh()        
                    
                        f1.write("\n\r")
                        f1.write("Test case %s  =  FAIL\n\r" % testcase)

                        f4.write("\n\r")
                        f4.write("Test case %s  =  FAIL\n\r" % testcase)
                                            
                        # create .FAIL test result
                        testcaseresult = os.getcwd() + "\\" + listcfgfilenames[count] + '.FAIL'
                    
                        f2 = open(testcaseresult, "w")
                        f2.write("Test case  %s  =  FAIL\n\r" % listcfgfilenames[count])
                                    
                except:
                    status = 1    # set to 1 on error
               
                    self.SetStatusText("Test case %s  =  FAIL\n\r % testcase")
                    self.Refresh()        

                    f1.write("Test case %s  =  FAIL\n\r" % testcase)

                    # create .FAIL test result
                    testcaseresult = os.getcwd() + "\\" + listcfgfilenames[count] + '.FAIL'                    
                    f2 = open(testcaseresult, "w")
                    f2.write("Test case %s  =  FAIL\n\r" % testcase)
                                                                 
                    f4.write("Test case %s  =  FAIL\n\r" % testcase)                                                

                self.SetStatusText("------- DONE ------- Running  %s  completed.\n\r" % testcase)
                self.Refresh()       

                # increment the count
                count = count + 1

            # close report running list of tests
            f1.close()
            f2.close()
            f4.close()

    


class ProcessSO():


    @staticmethod
    def Run_MSAG_test(f1, Config, e_results, cfg_file, pr, ecode):
        """
        Run the MSAG test with provided CFG file
        """
        #write log
        f1.write("Running test case = %s\n\r" % cfg_file)
        f1.write("\n\r")
        
        #obtain expected results from CFG file
        SO_utils.Log_Starting_Process("OBTAINING EXPECTED RESULT FROM CFG FILE", f1)     
        verifyCFGfile = SO_utils.msag_obtain_expect_result_from_cfgfile(f1, cfg_file, Config, e_results)

        c_err_code = {}
        verifyCFGFileOK, c_err_code = verifyCFGfile
        if verifyCFGFileOK:            
            #copy dat file to process
            verifyDATfile = SO_utils.msag_copy_dat_file_to_process(e_results, f1, mapdrive)

            if verifyDATfile:

                #write log
                f1.write("Watchdog function is waiting for file to process\n\r")
                f1.write("Max timeout = %s\n\r" % e_results[6])

                #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
                
                if os.path.exists(mapdrive + "\\"):
                      dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
                else: 
                      dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

                timeout = e_results[6]
                
                try:         
                    # call watchdog function with pattern matching
                    waiting_for_file(dest, int(timeout))
                    
                except:
                    # handle watchdog error
                    f1.write("Exception in watchdog function\n\r")
                    
                f1.write("Watchdog function caught the action. Done\n\r")

                #Verify if there is PERR file exists, then obtain the processing error from PERR file, then no more testing.
                perrfile = e_results[1].split('.')
                a_perrfile = perrfile[0] + '.' + 'perr'
                perror_description = ''
                
                # verify PERR file processing
                #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
                #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

                if os.path.exists(mapdrive + "\\"):
                      dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
                else: 
                      dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

                PERRfilepath = dest + a_perrfile
                SO_utils.Log_Starting_Process("VERIFICATION OF PERR FILE", f1)
                try:
                    if (os.path.exists(PERRfilepath)):           
                        #obtain processing error from PERR file
                        verifyPERR = SO_utils.msag_obtain_processing_error(e_results, f1, cfg_file, mapdrive)

                        perr_description, d_err_description, err_description, not_processed = verifyPERR
                        
                        if (not_processed == 'continue'):
                            #write log
                            if len(perr_description) > 0:
                                f1.write("Processing Error from  %s:\n\r %s\n" % (a_perrfile, perr_description))
                            if len(d_err_description) > 0:
                                f1.write("Error description from  %s:\n %s\n" % (a_perrfile, d_err_description))
                            if len(err_description) > 0:
                                f1.write("Reason description from  %s:\n %s\n" % (a_perrfile, err_description))

                            # continue to process if having the not_processed == 'continue'

                        else:

                            # else if perr_description is empty then return False, stop the process                           
                            #write log
                            if len(perr_description) > 0:
                                f1.write("Processing Error from  %s:\n  %s\n" % (a_perrfile, perr_description))
                            if len(d_err_description) > 0:
                                f1.write("Error description from  %s:\n  %s\n" % (a_perrfile, d_err_description))
                            if len(err_description) > 0:
                                f1.write("Reason description from  %s:\n  %s\n" % (a_perrfile, err_description))

                            # MSAG CFG: process error = e_results[14]
                            if (e_results[14] <> ""):
                                pat1 = "Error Processing File: [A-Za-z ']*. (.*)"
                                a1 = re.compile(pat1)
                                if len(err_description) > 0:
                                    if re.match(a1, err_description):
                                        tmp = len(err_description)
                                        p_description = err_description[23:tmp]
                                        p_desc = p_description.strip(' \n')
                                        e_desc = e_results[14].strip()
                                        if (e_desc == p_desc):
                                           f1.write("Expected processing error = [%s]\n" % e_desc)
                                           f1.write("Actual processing error = [%s]\n" % p_desc)
                                           return True

                            else:                            
                                return False

                    else:
                       f1.write("No occurence of  %s  in %s\n\r" % (a_perrfile, dest))
                            
                except:
                    #write log
                    f1.write("%s file not exists in %s\n\r" % (a_perrfile, dest))


#############################################################################################
                # process QERR file if exists
                SO_utils.Log_Starting_Process("VERIFICATION OF QERR FILE", f1)
                queueQERR = SO_utils.msag_queue_error_QERR_process(e_results, f1, mapdrive)
                if queueQERR:
                    return False

#############################################################################################    No Migrate for MSAG    ##########
                #SO_utils.Log_Starting_Process("VERIFICATION OF MSTA MERR FILES", f1)
                #msag_migrateMSTA = SO_utils.msag_migrate_MSTA_MERR_process(e_results, f1, ecode, c_err_code, mapdrive)
                #if msag_migrateMSTA:
                #    return True
#############################################################################################
                
                a_results  = []        #list to keep actual results        
                
                #obtain actual results from STA files 
                SO_utils.Log_Starting_Process("OBTAINING ACTUAL RESULT FROM STA FILE", f1)       
                verifySTAfile = SO_utils.msag_obtain_actual_result_from_STA_files(a_results, f1, e_results, mapdrive)

                if verifySTAfile:
                    
                    # no actual errors - processed with NO ERROR - no need to verify for error codes and counts in ERR, AUTOCORR                
                    if (a_results[5] <> '0'):
                                     
                        err_code   = []        #list of error codes
                        a_err_code = []        #list of actual result error count and error code in STA file
                                        
                        #obtain error codes from ERR file
                        SO_utils.Log_Starting_Process("OBTAINING ERROR CODES FROM ERR FILE", f1)
                        verifyERR = SO_utils.msag_obtain_error_codes_from_ERR_file(e_results, f1, err_code, ecode, mapdrive)

                        cnt_err_errorcode = {}
                        verifyERRfile, cnt_err_errorcode = verifyERR

                        if verifyERRfile:               
                            #verify error code in STA file
                            SO_utils.Log_Starting_Process("VERIFICATION EXPECTED AND ACTUAL RESULTS", f1)
                            verifySTA = SO_utils.msag_verify_error_code_in_STA_file(a_results, e_results, f1, a_err_code, ecode, mapdrive)

                            cnt_sta_errorcode = {}
                            verifySTAERR, cnt_sta_errorcode = verifySTA
                                                        
                            #compare count of insert records
                            if int(e_results[10]) == int(a_results[6]):
                                pass1 = True
                            else:
                                pass1 = False
                        
                            #compare count of processed record   
                            if int(e_results[7]) == int(a_results[3]):
                                pass2 = True
                            else:
                                pass2 = False
                        
                            #compare count of error record
                            if int(e_results[9]) == int(a_results[5]):
                                  i = 0
                                  for ecode in a_err_code:
                                      if a_err_code[i] in err_code:
                                          pass3 = True
                                      else:
                                          pass3 = False
                                      i = i + 1
                            else:
                                pass3 = False
                                    
                            # compare count of delete record
                            if int(e_results[11]) == int(a_results[7]):
                                pass4 = True
                            else:
                                pass4 = False

                            # compare count of not processed record
                            if int(e_results[8]) == int(a_results[4]):
                                pass5 = True
                            else:
                                pass5 = False 
                            
                            # compare count of befores record
                            if int(e_results[12]) == int(a_results[8]):
                                pass6 = True
                            else:
                                pass6 = False

                            # compare count of afters record
                            if int(e_results[13]) == int(a_results[9]):
                                pass7 = True
                            else:
                                pass7 = False                      

                            f1.write(SO_utils.ReportLine("Expected inserts", e_results[10], "Actual inserts", a_results[6], "pass1", pass1))
                            f1.write(SO_utils.ReportLine("Expected processed", e_results[7], "Actual processed", a_results[3], "pass2", pass2))
                            f1.write(SO_utils.ReportLine("Expected errors", e_results[9], "Actual errors", a_results[5], "pass3", pass3))
                            f1.write(SO_utils.ReportLine("Expected deletes", e_results[11], "Actual deletes", a_results[7], "pass4", pass4))
                            f1.write(SO_utils.ReportLine("Expected not processed", e_results[8], "Actual not processed", a_results[4], "pass5", pass5))
                            f1.write(SO_utils.ReportLine("Expected befores", e_results[12], "Actual befores", a_results[8], "pass6", pass6))
                            f1.write(SO_utils.ReportLine("Expected afters", e_results[13], "Actual afters", a_results[9], "pass7", pass7))

                            #c_err_code, c_autocorr_err_code, c_migrate_err_code
                            SO_utils.Log_Starting_Process("VERIFICATION OF EXPECTED ERROR CODE AND COUNT WITH ACTUAL RESULTS", f1)
                            pass88 = SO_utils.verify_error_code_in_cfg_with_actual_result(c_err_code, cnt_err_errorcode, cnt_sta_errorcode, f1)
                            pass8a, pass8b = pass88

                            pass8 = pass8a and pass8b

                            f1.write(SO_utils.ReportLine("Count error code from CFG file", c_err_code, "Count error code on STA file", cnt_sta_errorcode, "pass8a", pass8a))
                            f1.write(SO_utils.ReportLine("Count error code from ERR file", cnt_err_errorcode, "Count error code on STA file", cnt_sta_errorcode, "pass8b", pass8b))
                            f1.write("pass8 = %s\n\r" % pass8)

                            allpass = pass1 and pass2 and pass3 and pass4 and pass5 and pass6 and pass7 and pass8

                            # write log
                            f1.write("\n\r")                        
                            f1.write("allpass = %s    (pass1 = %s,  pass2 = %s,  pass3 = %s,  pass4 = %s,  pass5 = %s, pass6 = %s, pass7 = %s, pass8 = %s)\n\r" % (allpass,pass1,pass2,pass3,pass4,pass5,pass6,pass7, pass8))
                                                                                                          
                            return allpass


                    # else  ------------- of if (a_results[5] <> '0')
                    # actual error = 0 - No occurence of ERR - only DONE and STA
                    if (a_results[5] == '0'):
                        SO_utils.Log_Starting_Process("VERIFICATION OF EXPECTED RESULTS WITH ACTUAL RESULTS - NO OCCURENCE OF ERR - ONLY DONE and STA", f1)
                        allpass = SO_utils.msag_verify_expected_with_actual_results(e_results, a_results, f1)                                                                               
                        return allpass

                # not having STA file, test case is FAIL
                return False

            else:
                # not having CompanyID or UserName folder, test case is FAIL
                f1.write("Failed copying file. verifyDATFile = %s\n\r" % verifyDATfile)
                f2.write("Failed copying file. verifyDATFile = %s\n\r" % verifyDATfile)
                f4.write("Failed copying file. verifyDATFile = %s\n\r" % verifyDATfile)
            
                return False
        
        
        else:
            # not having CFG file, test case is FAIL
            f1.write("\n\r")
            f1.write("CFG file does not exists. verifyCFGFile = %s\n\r" % verifyCFGfile)
            f2.write("\n\r")
            f2.write("CFG file does not exists. verifyCFGFile = %s\n\r" % verifyCFGfile)
            f4.write("\n\r")
            f4.write("CFG file does not exists. verifyCFGFile = %s\n\r" % verifyCFGfile)
                            
            return False



    @staticmethod
    def Run_test(f1, Config, e_results, testcase, pr, ecode):
        """
        Run the test with provided CFG file
        """
        #write log
        f1.write("Running test case = %s\n\r" % testcase)
        f1.write("\n\r")

        #obtain expected results from CFG file
        SO_utils.Log_Starting_Process("OBTAINING EXPECTED RESULT FROM CFG FILE", f1)
             
        verifyCFGFile = SO_utils.obtain_expect_result_from_cfgfile(f1, testcase, Config, e_results)

        verifyCFGFileOK, c_err_code, c_autocorr_err_code, c_migrate_err_code = verifyCFGFile

        if verifyCFGFileOK:            
            #copy dat file to process
            verifyDATfile = SO_utils.copy_dat_file_to_process(e_results, f1, mapdrive)

            if verifyDATfile:
                
                #write log
                f1.write("Watchdog function is waiting for file to process\n\r")
                f1.write("Max timeout = %s\n\r" % e_results[5])

                #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                if os.path.exists(mapdrive + "\\"): 
                      dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                else: 
                      dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                timeout = e_results[5]
                
                try:         
                    # call watchdog function with pattern matching
                    waiting_for_file(dest, int(timeout))
                    
                except:
                    # handle watchdog error
                    f1.write("Exception in watchdog function\n\r")
                    f1.write("\n\r")
                                       
                f1.write("Watchdog function caught the action. Done\n\r")
                f1.write("\n\r")

                #Verify if there is PERR file exists, then obtain the processing error from PERR file, then no more testing.
                perrfile = e_results[0].split('.')
                a_perrfile = perrfile[0] + '.' + 'perr'
                perror_description = ''
                
                # verify PERR file processing
                #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                if os.path.exists(mapdrive + "\\"):
                      dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                else: 
                      dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                PERRfilepath = dest + a_perrfile

                SO_utils.Log_Starting_Process("VERIFICATION OF PERR FILE", f1)

                try:
                    if (os.path.exists(PERRfilepath)):           
                        #obtain processing error from PERR file
                        #perr_description = SO_utils.obtain_processing_error(e_results, f1, cfg_file)

                        perr_description = ''
                        d_err_description = ''
                        err_description = ''
                        not_processed = ''

                        verifyPERR = SO_utils.obtain_processing_error(e_results, f1, testcase, mapdrive)
                        perr_description, d_err_description, err_description, not_processed = verifyPERR
                        
                        if (not_processed == 'continue'):
                            #write log
                            if len(perr_description) > 0:
                                f1.write("Processing Error from  %s:\n\r %s\n" % (a_perrfile, perr_description))
                            if len(d_err_description) > 0:
                                f1.write("Error description from  %s:\n %s\n" % (a_perrfile, d_err_description))
                            if len(err_description) > 0:
                                f1.write("Reason description from  %s:\n %s\n" % (a_perrfile, err_description))

                            # continue to process if having the not_processed == 'continue'

                        else:
                            # else if perr_description is empty then return False, stop the process
                            
                            #write log
                            if len(perr_description) > 0:
                                f1.write("Processing Error from  %s:\n  %s\n" % (a_perrfile, perr_description))
                            if len(d_err_description) > 0:
                                f1.write("Error description from  %s:\n  %s\n" % (a_perrfile, d_err_description))
                            if len(err_description) > 0:
                                f1.write("Reason description from  %s:\n  %s\n" % (a_perrfile, err_description))

                            # ALI CFG: process error = e_results[12]
                            if (e_results[12] <> ""):
                                pat1 = "Error Processing File: [A-Za-z ']*. (.*)"
                                a1 = re.compile(pat1)
                                if len(err_description) > 0:
                                    if re.match(a1, err_description):
                                        tmp = len(err_description)
                                        p_description = err_description[23:tmp]
                                        p_desc = p_description.strip(' \n')
                                        e_desc = e_results[12].strip()
                                        if ( e_desc == p_desc):
                                           f1.write("Expected processing error = [%s]\n" % e_desc)
                                           f1.write("Actual processing error = [%s]\n" % p_desc)
                                           return True
                                                                   
                            return False

                    else:
                       f1.write("No occurence of  %s  in %s\n\r" % (a_perrfile, dest))
         
                except:
                    #write log
                    f1.write("%s file not exists in %s\n\r" % (a_perrfile, dest))

###############################################################################################
                # process QERR file if exists
                SO_utils.Log_Starting_Process("VERIFICATION OF QERR FILE", f1)
                queueQERR = SO_utils.queue_error_QERR_process(e_results, f1, mapdrive)
                if queueQERR:
                    return False

################################################################################################
                SO_utils.Log_Starting_Process("VERIFICATION OF MSTA MERR FILE", f1)
                migrateMSTA = SO_utils.migrate_MSTA_MERR_process(e_results, f1, ecode, c_err_code, mapdrive)
                if migrateMSTA:
                    return True
################################################################################################

                autocorrfile = e_results[0].split('.')
                a_autocorrfile = autocorrfile[0] + '.' + 'autocor'

                #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                if os.path.exists(mapdrive + "\\"):
                        dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                else: 
                        dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                AUTOCORfilepath = dest + a_autocorrfile
                autocor = False

                #Verify if there is AUTOCOR file exists, then obtain the autocorrect from AUTOCOR file.
                try:
                    SO_utils.Log_Starting_Process("VERIFICATION OF AUTOCOR FILE", f1)
                    if  os.path.exists(AUTOCORfilepath):
                        autocor_err_code = {}                       
                        autocor_err_code, a_autocorrected = SO_utils.obtain_autocorrection(e_results, f1, mapdrive)
                                       
                        if a_autocorrected != 0:                                    
                            # compare count of autocorrect record
                            if int(e_results[11]) == int(a_autocorrected):
                                autocor = True
                            else:
                                autocor = False

                            f1.write("From AUTOCOR file: autocorr = %s - a_autocorrected = %s\n" % (autocor, a_autocorrected))
                            if (len(autocor_err_code) > 0):
                                 f1.write("autocor_err_code = %s\n" % autocor_err_code)
                                                             
                    else:

                        f1.write("No occurence of  %s  in %s\n\r" % (a_autocorrfile, dest))                            
                except:
                    #MsgBox("Read AUTOCOR file exception.\n\r",'Exception Error')
                    f1.write("Read AUTOCOR file exception.\n\r")


################################################################################################
                
                a_results  = []        #list to keep actual results        
                
                #obtain actual results from STA files
                SO_utils.Log_Starting_Process("OBTAINING ACTUAL RESULT FROM STA FILE", f1)        
                verifySTAfile = SO_utils.obtain_actual_result_from_STA_files(a_results, f1, e_results, mapdrive)

                if verifySTAfile:
                    
                    # no actual errors - processed with NO ERROR - no need to verify for error codes and counts in ERR                
                    if ((a_results[5] <> '0') and (not autocor)):
                    
                        err_code   = []        #list of error codes
                        a_err_code = []        #list of actual result error count and error code in STA file
                                        
                        #obtain error codes from ERR file
                        SO_utils.Log_Starting_Process("OBTAIN ERROR CODES FROM ERR FILE", f1)
                        verifyERR = SO_utils.obtain_error_codes_from_ERR_file(e_results, f1, err_code, ecode, mapdrive)
                        cnt_err_errorcode = {}
                        verifyERRfile, cnt_err_errorcode = verifyERR

                        if verifyERRfile:               
                            #verify error code in STA file
                            verifySTA = SO_utils.verify_error_code_in_STA_file(a_results, e_results, f1, a_err_code, ecode, mapdrive)
                            cnt_sta_errorcode = {}
                            verifySTAERR, cnt_sta_errorcode = verifySTA

                            SO_utils.Log_Starting_Process("VERIFICATION OF EXPECTED AND ACTUAL RESULTS", f1)
                                
                            #compare count of insert records
                            if int(e_results[6]) == int(a_results[3]):
                                pass1 = True
                            else:
                                pass1 = False
                        
                            #compare count of processed record   
                            if int(e_results[7]) == int(a_results[4]):
                                pass2 = True
                            else:
                                pass2 = False
                        
                            #compare count of error record
                            if int(e_results[8]) == int(a_results[5]):
                                  i = 0
                                  for ecode in a_err_code:
                                      if a_err_code[i] in err_code:
                                          pass3 = True
                                      else:
                                          pass3 = False
                                      i = i + 1
                            else:
                                pass3 = False

                            # compare count of delete record
                            if int(e_results[9]) == int(a_results[6]):
                                pass4 = True
                            else:
                                pass4 = False

                            # compare count of changes record
                            if int(e_results[10]) == int(a_results[7]):
                                pass5 = True
                            else:
                                pass5 = False  


                            # compare count of unlock record
                            if int(e_results[14]) == int(a_results[9]):
                                pass6 = True
                            else:
                                pass6 = False 

                            # compare count of pilot delete record
                            if int(e_results[15]) == int(a_results[11]):
                                pass7 = True
                            else:
                                pass7 = False 

                            f1.write(SO_utils.ReportLine("Expected inserts", e_results[6], "Actual inserts", a_results[3], "pass1", pass1))
                            f1.write(SO_utils.ReportLine("Expected processed", e_results[7], "Actual processed", a_results[4], "pass2", pass2))
                            f1.write(SO_utils.ReportLine("Expected errors", e_results[8], "Actual errors", a_results[5], "pass3", pass3))
                            f1.write(SO_utils.ReportLine("Expected deletes", e_results[9], "Actual deletes", a_results[6], "pass4", pass4))
                            f1.write(SO_utils.ReportLine("Expected changes", e_results[10], "Actual changes", a_results[7], "pass5", pass5))
                            f1.write(SO_utils.ReportLine("Expected unlock", e_results[14], "Actual unlock", a_results[9], "pass6", pass6))
                            f1.write(SO_utils.ReportLine("Expected pilot delete", e_results[15], "Actual pilot delete", a_results[11], "pass7", pass7))

                            #c_err_code, c_autocorr_err_code, c_migrate_err_code
                            SO_utils.Log_Starting_Process("VERIFICATION OF EXPECTED ERROR CODE AND COUNT WITH ACTUAL RESULTS", f1)
                            pass88 = SO_utils.verify_error_code_in_cfg_with_actual_result(c_err_code, cnt_err_errorcode, cnt_sta_errorcode, f1)
                            pass8a, pass8b = pass88

                            pass8 = pass8a and pass8b

                            f1.write(SO_utils.ReportLine("Count error code from CFG file", c_err_code, "Count error code on STA file", cnt_sta_errorcode, "pass8a", pass8a))
                            f1.write(SO_utils.ReportLine("Count error code from ERR file", cnt_err_errorcode, "Count error code on STA file", cnt_sta_errorcode, "pass8b", pass8b))
                            f1.write("pass8 = %s\n\r" % pass8)
                            
                            allpass = pass1 and pass2 and pass3 and pass4 and pass5 and pass6 and pass7 and pass8
                                                                               
                            return allpass

                    if (autocor):                        
                        # c_autocor_err_code      - obtain autocor type error code from CFG file
                        # autocor_err_code        - obtain autocor error code from AUTOCORR file                
                        SO_utils.Log_Starting_Process("VERIFICATION OF EXPECTED AUTOCOR ERROR CODE AND COUNT WITH ACTUAL RESULTS", f1)
                        pass9 = SO_utils.verify_error_code_in_cfg_with_autocor_file(c_autocorr_err_code, autocor_err_code, f1)
                        f1.write(SO_utils.ReportLine("Verify error code from CFG file", c_autocorr_err_code, "Verify error code on AUTOCOR file", autocor_err_code, "pass9", pass9))

                        #else a_results[5] == 0 - count of processed records and count of changes (or also count of inserts records)
                        SO_utils.Log_Starting_Process("VERIFICATION ACTUAL RESULTS AND TEST CASE RESULT", f1)

                        if (e_results[8] == a_results[5]):
                            pass10 = True
                            f1.write(SO_utils.ReportLine("Expected errors", e_results[8], "Actual errors", a_results[5], "pass10", pass10))

                        allpass = pass9 and pass10
                        f1.write("allpass = %s   (pass9 = %s, pass10 = %s)\n" % (allpass, pass9, pass10))
                        return allpass


                    # else     ----- of if ((a_results[5] <> '0') and (not autocor))
                    # actual error = 0 - No occurence of ERR and AUTOCOR
                    if (a_results[5] == '0'):
                        SO_utils.Log_Starting_Process("VERIFICATION OF EXPECTED RESULTS WITH ACTUAL RESULTS - NO OCCURENCE OF ERR - ONLY DONE and STA", f1)
                        allpass = SO_utils.verify_expected_with_actual_results(e_results, a_results, f1)                                                                               
                        return allpass

                else:

                    # not having STA file, test case is FAIL
                    return False
            
            else:
                # not having CompanyID or UserName folder, test case is FAIL
                f1.write("Failed copying file. verifyDATFile = %s\n\r" % verifyDATfile)
                f2.write("Failed copying file. verifyDATFile = %s\n\r" % verifyDATfile)
                f4.write("Failed copying file. verifyDATFile = %s\n\r" % verifyDATfile)
            
                return False
        
        else:
            # not having CFG file, test case is FAIL
            f1.write("CFG file does not exists. verifyCFGFile = %s\n\r" % verifyCFGfile)
            f2.write("CFG file does not exists. verifyCFGFile = %s\n\r" % verifyCFGfile)
            f4.write("CFG file does not exists. verifyCFGFile = %s\n\r" % verifyCFGfile)
                    
            return False



class App(wx.App):
    def __init__(self, redirect):
        wx.App.__init__(self, redirect)
        
    def OnInit(self):
        try:
            # ensure no other mapping mapdrive
            NetUseDeleteConnection_mapdrive()

            # Ask user to login
            dlg = ConnectRemoteDialog()
            if (dlg.ShowModal() == wx.ID_OK):
                 if (self.logged_in):
                     print "Connected"
                     self.Show()

            dlg.Destroy()       
               
            frame = main_window(None, 'Service Orders Processing')

            return True

        except:
            print "Cancel was pressed on ConnectRemoteDialog"


def Define_global_variables():
    """
    define all global variables
    """
    mapdrive = "Y:"
    local_mapdrive = "C:"
    prov_parentpath = "Intrepid_Admin_SOI_Files"
    SOI_data_format = "NENA 2.1 format"
    ALI_REC_LENGTH = 512
    MSAG_REC_LENGTH = 200

    # temp file for appending created new ALI SOI data file
    julianday = SO_utils.get_julianday()
    currdate = time.strftime("%x")
    today = currdate.replace('/','-')
    currpath = os.getcwd()

    Adatafile = "A_" + today + " " + str(julianday) + "001.dat"
    ALIpath = currpath + "\\" + Adatafile

    # open dat file
    A_datfile = open(ALIpath, 'a')           # appending mode


    Mdatafile = "M_" + today + " " + str(julianday) + "001.dat"
    MSAGpath = currpath + "\\" + Mdatafile

    # open dat file
    M_datfile = open(MSAGpath, 'a')           # appending mode


    return mapdrive, local_mapdrive, prov_parentpath, SOI_data_format, ALI_REC_LENGTH, MSAG_REC_LENGTH, A_datfile, M_datfile, ALIpath, MSAGpath

    #return mapdrive, local_mapdrive, prov_parentpath, SOI_data_format, ALI_REC_LENGTH, MSAG_REC_LENGTH


###################################################################################
if __name__== '__main__':

    # global variables
    globalvars = Define_global_variables()
    mapdrive, local_mapdrive, prov_parentpath, SOI_data_format, ALI_REC_LENGTH, MSAG_REC_LENGTH, A_datfile, M_datfile, ALIpath, MSAGpath = globalvars

    app = App(0)
    app.MainLoop()

###################################################################################