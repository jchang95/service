#! /usr/bin/env python

# SO_utils.py
#    Utilities to use with SOProcessing.py
#
#

import os
import os.path
import shutil                      #for copy file from source to destination directory
import re                          #for regular expression
import time                        #for current date and time
import wx                          #for wxpython
import datetime                    #for get_julianday()
from stat import S_ISREG, ST_CTIME, ST_MODE, ST_MTIME   #for sort_dir_date_filename
import sys                         #for sort_dir_date_filename
import glob                        #for get_latest_file_same_extension
import string                      #for CharValidator
from operator import itemgetter    #for errorcode dictionary
import wx.calendar as cal          #for Calendar class
import wx.lib.mixins.listctrl      #for CustColumnSorterMixin
import locale                      #for CustColumnSorterMixin

import wx.combo                    #for DateCtrl, CalendarDlg
import wx.calendar                 #for DateCtrl, CalendarDlg
from datetime import date as dt    #for DateCtrl, CalendarDlg

import wx.calendar as cal          #for Calendar

import string
import random
from random import randint                  #for random number  --- usage:  rndint = randint(0,100),  rndint = 50
import wx.lib.agw.pybusyinfo as PBI         #for busy dialog



def ask(parent=None, message='', default_value=''):
    """
    dialog to enter in text box with question
    """
    dlg = wx.TextEntryDialog(parent, message, defaultValue=default_value)
    dlg.ShowModal()
    result = dlg.GetValue()
    dlg.Destroy()
    return result


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """
    randomize 6 alphanumeric chrs
    usage:
    idstr = id_generator()
    'KHF5CD'
    idstr2 = id_generator(3, 'KHF5CD')
    'KKH'
    another example: i1 = id_generator(3,id_generator())
    output:  i1 = 'Q00'
    """
    return ''.join(random.choice(chars) for _ in range(size))


def stopwatch(seconds):
    start = time.time()
    time.clock()    
    elapsed = 0
    while elapsed < seconds:
        elapsed = time.time() - start
        inText = "loop cycle time: %f, seconds count: %02d" % (time.clock() , elapsed)
        print inText

        # display busy dialog
        message = "Please wait..."
        busy = PBI.PyBusyInfo(message, parent=None, title="Processing",)
        wx.Yield()        
        for indx in xrange(seconds):
            wx.MilliSleep(10)
        del busy
         
        time.sleep(1)


def  ReplaceFileExtension(filenamewithextension, replacewith):
    """
    Use filename.rpartition('.') to replace with new extension.
    Usage:
    file1 = "TestingFiles.mdf" 
    file2 = ReplaceFileExtension(file1, "ldf")
    output: file2 = "TestingFiles.ldf"
    """
    (prefix, sep, suffix) = filenamewithextension.rpartition('.')
    newfilename = prefix + "." + replacewith
    return newfilename


"""
  Usage:
    Set up on a panel:
        input_format = '%d-%m-%Y'
        display_format = '%a %d %b %Y'     # Fri Mar 25 2016

        #display_format = '%d/%m/%Y'        # 25/03/2016

        wx.StaticText(self, -1, 'Invoice date', pos=(50, 80))

        self.d = DateCtrl(self, size=wx.Size(130, -1), pos=wx.Point(150, 80),
            input_format=input_format, display_format=display_format,
            title='Invoice date', default_to_today=False, allow_null=False)

        self.first_time = True  # don't validate date first time
        self.SetFocus() 
"""
class DateCtrl(wx.combo.ComboCtrl):
    INPUT_FORMAT = 0
    DISPLAY_FORMAT = 1

    def __init__(self, parent, size, pos, input_format, display_format,
            title, default_to_today, allow_null):
        wx.combo.ComboCtrl.__init__(self, parent, size=size, pos=pos)

        self.input_format = input_format
        self.display_format = display_format
        self.title = title
        self.default_to_today = default_to_today
        self.allow_null = allow_null

        self.TextCtrl.Bind(wx.EVT_SET_FOCUS, self.on_got_focus)
        self.TextCtrl.Bind(wx.EVT_CHAR, self.on_char)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_mouse_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.on_mouse_leave)

        self.nav = False  # force navigation after selecting date
        self.is_valid = True  # unlike IsValid(), a blank date can be valid
        self.current_format = self.DISPLAY_FORMAT
        self.date = wx.DateTime()
        self.setup_button()  # create a custom button for popup
        (self.blank_string, self.yr_pos, self.mth_pos, self.day_pos,
            self.literal_pos) = self.setup_input_format()

        # set up button coords for mouse hit-test
        self.b_x1 = self.TextRect[2] - 2
        self.b_y1 = self.TextRect[1] - 1
        self.b_x2 = self.b_x1 + self.ButtonSize[0] + 3
        self.b_y2 = self.b_y1 + self.ButtonSize[1] + 1
        self.on_button = False

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.show_tooltip)

    def on_mouse_enter(self, evt):
        if self.b_x1 <= evt.X <= self.b_x2:
            if self.b_y1 <= evt.Y <= self.b_y2:
                self.on_button = True
                self.timer.Start(500, oneShot=True)
        evt.Skip()

    def on_mouse_leave(self, evt):
        if self.on_button:
            self.on_button = False
            self.timer.Stop()
        evt.Skip()

    def show_tooltip(self, evt):
        abs_x, abs_y = self.ScreenPosition
        rect = wx.Rect(abs_x+self.b_x1, abs_y+self.b_y1,
            self.b_x2-self.b_x1+1, self.b_y2-self.b_y1+1)
        tip = wx.TipWindow(self, 'Show calendar\n(F4 or space)')
        # tip will be destroyed when mouse leaves this rect
        tip.SetBoundingRect(rect)

    def setup_button(self):  # copied directly from demo
        # make a custom bitmap showing "..."
        bw, bh = 14, 16
        bmp = wx.EmptyBitmap(bw, bh)
        dc = wx.MemoryDC(bmp)

        # clear to a specific background colour
        bgcolor = wx.Colour(255, 254, 255)
        dc.SetBackground(wx.Brush(bgcolor))
        dc.Clear()

        # draw the label onto the bitmap
        label = u'\u2026'  # unicode ellipsis
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        dc.SetFont(font)
        tw, th = dc.GetTextExtent(label)
        dc.DrawText(label, (bw-tw)/2, (bw-tw)/2)
        del dc

        # now apply a mask using the bgcolor
        bmp.SetMaskColour(bgcolor)

        # and tell the ComboCtrl to use it
        self.SetButtonBitmaps(bmp, True)

    def setup_input_format(self):
        """
        Modify the defined input format to a string where each character
        represents one character of the input string.
        Generate and return a blank string to fill in the control.
        Return positions within the string of yr, mth, day and literals.
        """
        format = self.input_format
        blank_string = format

        yr_pos = format.find('%y')
        if yr_pos > -1:
            blank_string = blank_string[:yr_pos]+'  '+blank_string[yr_pos+2:]
            yr_pos = (yr_pos, yr_pos+2)
        else:
            yr_pos = format.find('%Y')
            if yr_pos > -1:
                blank_string = blank_string[:yr_pos]+'    '+blank_string[yr_pos+2:]
                format = format[:yr_pos+2]+'YY'+format[yr_pos+2:]
                yr_pos = (yr_pos, yr_pos+4)

        mth_pos = format.find('%m')
        if mth_pos > -1:
            blank_string = blank_string[:mth_pos]+'  '+blank_string[mth_pos+2:]
            mth_pos = (mth_pos, mth_pos+2)

        day_pos = format.find('%d')
        if day_pos > -1:
            blank_string = blank_string[:day_pos]+'  '+blank_string[day_pos+2:]
            day_pos = (day_pos, day_pos+2)

        literal_pos = [i for (i, ch) in enumerate(blank_string)
            if blank_string[i] == format[i]]

        return blank_string, yr_pos, mth_pos, day_pos, literal_pos

    # Overridden from ComboCtrl, called when the combo button is clicked
    def OnButtonClick(self):
        self.SetFocus()  # in case we do not have focus
        dlg = CalendarDlg(self)
        dlg.CentreOnScreen()
        if dlg.ShowModal() == wx.ID_OK:
            self.date = dlg.cal.Date
            self.Value = self.date.Format(self.display_format)
            self.current_format = self.DISPLAY_FORMAT
            self.nav = True  # force navigation to next control
        dlg.Destroy()

    # Overridden from ComboCtrl to avoid assert since there is no ComboPopup
    def DoSetPopupControl(self, popup):
        pass

    def on_got_focus(self, evt):
        if self.nav:  # user has made a selection, so move on
            self.nav = False
            wx.CallAfter(self.Navigate)
        else:
            text_ctrl = self.TextCtrl
            if not self.is_valid:  # re-focus after error
                pass  # leave Value alone
            elif self.date.IsValid():
                text_ctrl.Value = self.date.Format(self.input_format)
            elif self.default_to_today:
                self.date = wx.DateTime.Today()
                text_ctrl.Value = self.date.Format(self.input_format)
            else:
                text_ctrl.Value = self.blank_string
            self.current_format = self.INPUT_FORMAT
            text_ctrl.InsertionPoint = 0
            text_ctrl.SetSelection(-1, -1)
            text_ctrl.pos = 0
        evt.Skip()

    def convert_to_wx_date(self):  # conversion and validation method
        self.is_valid = True

        value = self.Value
        if value in (self.blank_string, ''):
            if self.default_to_today:
                self.date = wx.DateTime.Today()
                self.Value = self.date.Format(self.display_format)
            elif self.allow_null:
                self.date = wx.DateTime()
                self.Value = ''
            else:
                wx.CallAfter(self.display_error, 'Date is required')
            return

        if self.current_format == self.DISPLAY_FORMAT:  # no validation reqd
            self.TextCtrl.SetSelection(0, 0)
            return

        today = dt.today()

        if self.yr_pos == -1:  # 'yr' not an element of input_format
            year = today.year
        else:
            year = value[self.yr_pos[0]:self.yr_pos[1]].strip()
            if year == '':
                year = today.year
            elif len(year) == 2:
                # assume year is in range (today-90) to (today+10)
                year = int(year) + int(today.year/100)*100
                if year - today.year > 10:
                    year -= 100
                elif year - today.year < -90:
                    year += 100
            else:
                year = int(year)

        if self.mth_pos == -1:  # 'mth' not an element of input_format
            month = today.month
        else:
            month = value[self.mth_pos[0]:self.mth_pos[1]].strip()
            if month == '':
                month = today.month
            else:
                month = int(month)

        if self.day_pos == -1:  # 'day' not an element of input_format
            day = today.day
        else:
            day = value[self.day_pos[0]:self.day_pos[1]].strip()
            if day == '':
                day = today.day
            else:
                day = int(day)

        try:
            date = dt(year, month, day)  # validate using python datetime
        except ValueError as error:  # gives a meaningful error message
            wx.CallAfter(self.display_error, error.args[0])
        else:  # date is valid
            self.date = wx.DateTimeFromDMY(day, month-1, year)
            self.Value = self.date.Format(self.display_format)
            self.current_format = self.DISPLAY_FORMAT

    def display_error(self, errmsg):
        self.is_valid = False
        self.SetFocus()
        dlg = wx.MessageDialog(self, errmsg,
            self.title, wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def on_char(self, evt):
        text_ctrl = self.TextCtrl
        code = evt.KeyCode
        if code in (wx.WXK_SPACE, wx.WXK_F4) and not evt.AltDown():
            self.OnButtonClick()
            return
        max = len(self.blank_string)
        if code in (wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_HOME, wx.WXK_END):
            if text_ctrl.Selection == (0, max):
                text_ctrl.SetSelection(0, 0)
            if code == wx.WXK_LEFT:
                if text_ctrl.pos > 0:
                    text_ctrl.pos -= 1
                    while text_ctrl.pos in self.literal_pos:
                        text_ctrl.pos -= 1
            elif code == wx.WXK_RIGHT:
                if text_ctrl.pos < max:
                    text_ctrl.pos += 1
                    while text_ctrl.pos in self.literal_pos:
                        text_ctrl.pos += 1
            elif code == wx.WXK_HOME:
                text_ctrl.pos = 0
            elif code == wx.WXK_END:
                text_ctrl.pos = max
            text_ctrl.InsertionPoint = text_ctrl.pos
            return
        if code in (wx.WXK_BACK, wx.WXK_DELETE):
            if text_ctrl.Selection == (0, max):
                text_ctrl.Value = self.blank_string
                text_ctrl.SetSelection(0, 0)
            if code == wx.WXK_BACK:
                if text_ctrl.pos == 0:
                    return
                text_ctrl.pos -= 1
                while text_ctrl.pos in self.literal_pos:
                    text_ctrl.pos -= 1
            elif code == wx.WXK_DELETE:
                if text_ctrl.pos == max:
                    return
            curr_val = text_ctrl.Value
            text_ctrl.Value = curr_val[:text_ctrl.pos]+' '+curr_val[text_ctrl.pos+1:]
            text_ctrl.InsertionPoint = text_ctrl.pos
            return
        if code in (wx.WXK_TAB, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) or code > 255:
            evt.Skip()
            return
        if text_ctrl.pos == max:
            wx.Bell()
            return
        ch = chr(code)
        if ch not in ('0123456789'):
            wx.Bell()
            return
        if text_ctrl.Selection == (0, max):
            curr_val = self.blank_string
        else:
            curr_val = text_ctrl.Value
        text_ctrl.Value = curr_val[:text_ctrl.pos]+ch+curr_val[text_ctrl.pos+1:]
        text_ctrl.pos += 1
        while text_ctrl.pos in self.literal_pos:
            text_ctrl.pos += 1
        text_ctrl.InsertionPoint = text_ctrl.pos

"""
To be used with DateCtrl above
"""
class CalendarDlg(wx.Dialog):
    def __init__(self, parent):

        wx.Dialog.__init__(self, parent, title=parent.title)
        panel = wx.Panel(self, -1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        cal = wx.calendar.CalendarCtrl(panel, date=parent.date)

        if sys.platform != 'win32':
            # gtk truncates the year - this fixes it
            w, h = cal.Size
            cal.Size = (w+25, h)
            cal.MinSize = cal.Size

        sizer.Add(cal, 0)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add((0, 0), 1)
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_ok.SetDefault()
        button_sizer.Add(btn_ok, 0, wx.ALL, 2)
        button_sizer.Add((0, 0), 1)
        btn_can = wx.Button(panel, wx.ID_CANCEL)
        button_sizer.Add(btn_can, 0, wx.ALL, 2)
        button_sizer.Add((0, 0), 1)
        sizer.Add(button_sizer, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Fit(panel)
        self.ClientSize = panel.Size

        cal.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        cal.SetFocus()
        self.cal = cal

    def on_key_down(self, evt):
        code = evt.KeyCode
        if code == wx.WXK_TAB:
            self.cal.Navigate()
        elif code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.EndModal(wx.ID_OK)
        elif code == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        else:
            evt.Skip()



class CustColumnSorterMixin(wx.lib.mixins.listctrl.ColumnSorterMixin):
    """
    # Change this to your settings to use CustColumnSorterMixin
    date_re = re.compile("(\d{2})-(\d{2})-(\d{4})")

    """
    def __init__(self, numColumns):
        wx.lib.mixins.listctrl.ColumnSorterMixin(self, numColumns)

    def GetColumnSorter(self):
        return self.CustColumnSorter

    def CustColumnSorter(self, key1, key2):
        col = self._col
        ascending = self._colSortFlag[col]
        item1 = self.itemDataMap[key1][col]
        item2 = self.itemDataMap[key2][col]

        alpha = date_re.match(item1)
        beta =  date_re.match(item2)
        if alpha and beta:
            # Change these from your settings to YYYYMMDD
            item1 = alpha.group(3)+alpha.group(1)+alpha.group(2)
            item2 =  beta.group(3)+ beta.group(1)+ beta.group(2)

            item1 = int(item1)
            item2 = int(item2)

        #--- Internationalization of string sorting with locale module
        if type(item1) == type('') or type(item2) == type(''):
            cmpVal = locale.strcoll(str(item1), str(item2))
        else:
            cmpVal = cmp(item1, item2)
        #---

        # If the items are equal then pick something else to make the sort value unique
        if cmpVal == 0:
            cmpVal = cmp(*self.GetSecondarySortValues(col, key1, key2))

        if ascending:
            return cmpVal
        else:
            return -cmpVal


class DragListStriped(wx.ListCtrl):
    """
    USAGE: =========================================================
    if __name__ == "__main__":
    firstNameList = ["Ben", "Bruce", "Clark", "Dick"]
    lastNameList =  ["Grimm","Wayne", "Kent", "Grayson"]
    superNameList = ["The Thing", "Batman", "Superman", "Robin"]

    class ThisApp(wx.App):
        def OnInit(self):
            self.myFrame = wx.Frame(None, title='Drag List Striped Example')
            self.myFrame.Show(True)
            self.SetTopWindow(self.myFrame)
            return True

    myApp = ThisApp(redirect=False)
    dls = DragListStriped(myApp.myFrame, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
    dls.InsertColumn(0, "First Name")
    dls.InsertColumn(1, "Last Name")
    dls.InsertColumn(2, "Superhero Name")
    sizer = wx.BoxSizer()
    myApp.myFrame.SetSizer(sizer)
    sizer.Add(dls, proportion=1, flag=wx.EXPAND)

    for index in range(len(firstNameList)):
        dls.InsertStringItem(index, firstNameList[index])
        dls.SetStringItem(index, 1, lastNameList[index])
        dls.SetStringItem(index, 2, superNameList[index])
    myApp.myFrame.Layout()
    dls._onStripe()
    myApp.MainLoop()

    """

    def __init__(self, *arg, **kw):
        wx.ListCtrl.__init__(self, *arg, **kw)

        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._onDrag)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onSelect)
        self.Bind(wx.EVT_LEFT_UP,self._onMouseUp)
        self.Bind(wx.EVT_LEFT_DOWN, self._onMouseDown)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._onLeaveWindow)
        self.Bind(wx.EVT_ENTER_WINDOW, self._onEnterWindow)
        self.Bind(wx.EVT_LIST_INSERT_ITEM, self._onInsert)
        self.Bind(wx.EVT_LIST_DELETE_ITEM, self._onDelete)

        #---------------
        # Variables
        #---------------
        self.IsInControl=True
        self.startIndex=-1
        self.dropIndex=-1
        self.IsDrag=False
        self.dragIndex=-1

    def _onLeaveWindow(self, event):
        self.IsInControl=False
        self.IsDrag=False
        event.Skip()

    def _onEnterWindow(self, event):
        self.IsInControl=True
        event.Skip()

    def _onDrag(self, event):
        self.IsDrag=True
        self.dragIndex=event.m_itemIndex
        event.Skip()
        pass

    def _onSelect(self, event):
        self.startIndex=event.m_itemIndex
        event.Skip()

    def _onMouseUp(self, event):
        # Purpose: to generate a dropIndex.
        # Process: check self.IsInControl, check self.IsDrag, HitTest, compare HitTest value
        # The mouse can end up in 5 different places:
        # Outside the Control
        # On itself
        # Above its starting point and on another item
        # Below its starting point and on another item
        # Below its starting point and not on another item

        if self.IsInControl==False:       #1. Outside the control : Do Nothing
            self.IsDrag=False
        else:                                   # In control but not a drag event : Do Nothing
            if self.IsDrag==False:
                pass
            else:                               # In control and is a drag event : Determine Location
                self.hitIndex=self.HitTest(event.GetPosition())
                self.dropIndex=self.hitIndex[0]
                # -- Drop index indicates where the drop location is; what index number
                #---------
                # Determine dropIndex and its validity
                #--------
                if self.dropIndex==self.startIndex or self.dropIndex==-1:    #2. On itself or below control : Do Nothing
                    pass
                else:
                    #----------
                    # Now that dropIndex has been established do 3 things
                    # 1. gather item data
                    # 2. delete item in list
                    # 3. insert item & it's data into the list at the new index
                    #----------
                    dropList=[]         # Drop List is the list of field values from the list control
                    thisItem=self.GetItem(self.startIndex)
                    for x in range(self.GetColumnCount()):
                        dropList.append(self.GetItem(self.startIndex,x).GetText())
                    thisItem.SetId(self.dropIndex)
                    self.DeleteItem(self.startIndex)
                    self.InsertItem(thisItem)
                    for x in range(self.GetColumnCount()):
                        self.SetStringItem(self.dropIndex,x,dropList[x])
            #------------
            # I don't know exactly why, but the mouse event MUST
            # call the stripe procedure if the control is to be successfully
            # striped. Every time it was only in the _onInsert, it failed on
            # dragging index 3 to the index 1 spot.
            #-------------
            # Furthermore, in the load button on the wxFrame that this lives in,
            # I had to call the _onStripe directly because it would occasionally fail
            # to stripe without it. You'll notice that this is present in the example stub.
            # Someone with more knowledge than I probably knows why...and how to fix it properly.
            #-------------
        self._onStripe()
        self.IsDrag=False
        event.Skip()

    def _onMouseDown(self, event):
        self.IsInControl=True
        event.Skip()

    def _onInsert(self, event):
        # Sequencing on a drop event is:
        # wx.EVT_LIST_ITEM_SELECTED
        # wx.EVT_LIST_BEGIN_DRAG
        # wx.EVT_LEFT_UP
        # wx.EVT_LIST_ITEM_SELECTED (at the new index)
        # wx.EVT_LIST_INSERT_ITEM
        #--------------------------------
        # this call to onStripe catches any addition to the list; drag or not
        self._onStripe()
        self.dragIndex=-1
        event.Skip()

    def _onDelete(self, event):
        self._onStripe()
        event.Skip()

    def _onStripe(self):
        if self.GetItemCount()>0:
            for x in range(self.GetItemCount()):
                if x % 2==0:
                    self.SetItemBackgroundColour(x,wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DLIGHT))
                else:
                    self.SetItemBackgroundColour(x,wx.WHITE)


###########################
# usage:
#f = open(detailrpt, "r")
#msg = f.read()
#f.close()                       
#dlg = SO_utils.ShowLastRun(self, msg, "Details report of all test runs\n\r")            
#dlg.ShowModal()     
#dlg.Destroy()
###########################
#
class ShowLastRun(wx.Dialog):
    def __init__(self, parent, msg_text, titletxt):
        wx.Dialog.__init__(self, parent, title=titletxt)
        
        text = wx.TextCtrl(self, -1, msg_text, size =(580,550), style=wx.TE_MULTILINE | wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL )        
        btnsizer = wx.BoxSizer()

        sizer.Add(text, 0, wx.EXPAND|wx.ALL, 5)       
        sizer.Add(btnsizer, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        
        self.SetSizerAndFit (sizer)



class Calendar(wx.Dialog):
    """
    USAGE:
    selected_date = ''
    Calendar(None, -1, 'calendar.py', selected_date)

    print selected_date
    """
    def __init__(self, parent, id, title, selected_date):
        wx.Dialog.__init__(self, parent, id, title)

        vbox = wx.BoxSizer(wx.VERTICAL)

        calend = cal.CalendarCtrl(self, -1, wx.DateTime_Now(),
            style = cal.CAL_SHOW_HOLIDAYS|cal.CAL_SEQUENTIAL_MONTH_SELECTION)
        vbox.Add(calend, 0, wx.EXPAND | wx.ALL, 20)
        self.Bind(cal.EVT_CALENDAR, self.OnCalSelected, id=calend.GetId())

        vbox.Add((-1, 20))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.text = wx.StaticText(self, -1, 'Date')
        hbox.Add(self.text)
        vbox.Add(hbox, 0,  wx.LEFT, 8)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        btn = wx.Button(self, -1, 'Ok')
        hbox2.Add(btn, 1)
        vbox.Add(hbox2, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 20)

        self.Bind(wx.EVT_BUTTON, self.OnQuit, id=btn.GetId())
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

        self.SetSizerAndFit(vbox)

        self.Show(True)
        self.Centre()


    def OnCalSelected(self, event):
        date = event.GetDate()
        dt = str(date).split(' ')
        s = ' '.join(str(s) for s in dt)
        self.text.SetLabel(s)
        selected_date = s
        print selected_date

    def OnQuit(self, event):
        self.Destroy()


"""
Usage: Run from a command DOS prompt:
      C:> python test_progress.py

"test_progress.py"

(insert class ProgressBar here!!)
if __name__ == "__main__":
    import sys
    import time
    count = 5
    print "starting things:"

    pb = ProgressBar(count)

    curProgress = 0
    #pb.plotProgress()
    
    while curProgress <= count:
        pb.setAndPlot(curProgress)
        curProgress += 1
        time.sleep(1)
    del pb

    print "done"

"""
class ProgressBar():
    DEFAULT_BAR_LENGTH = float(65)

    def __init__(self, end, start=0):
        self.end    = end
        self.start  = start
        self._barLength = ProgressBar.DEFAULT_BAR_LENGTH

        self.setLevel(self.start)
        self._plotted = False

    def setLevel(self, level, initial=False):
        self._level = level
        if level < self.start:  self._level = self.start
        if level > self.end:    self._level = self.end

        self._ratio = float(self._level - self.start) / float(self.end - self.start)
        self._levelChars = int(self._ratio * self._barLength)

    def plotProgress(self):
        sys.stdout.write("\r  %3i%% [%s%s]" %(
            int(self._ratio * 100.0),
            '#' * int(self._levelChars),
            ' ' * int(self._barLength - self._levelChars),
        ))
        sys.stdout.flush()
        self._plotted = True

    def setAndPlot(self, level):
        oldChars = self._levelChars
        self.setLevel(level)
        if (not self._plotted) or (oldChars != self._levelChars):
            self.plotProgress()

    def __del__(self):
        sys.stdout.write("\n")



class CharValidator(wx.PyValidator):
    """
    Validates data as it is entered into the text controls.
    Usage: count_errors = wx.TextCtrl(self, value="", size=(250, 20), validator=SO_utils.CharValidator('no-alpha')
    """

    def __init__(self, flag):
        wx.PyValidator.__init__(self)
        self.flag = flag
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        '''Required Validator method'''
        return CharValidator(self.flag)

    def Validate(self, win):
        return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    def OnChar(self, event):
        keycode = int(event.GetKeyCode())
        if keycode < 256:
            #print keycode
            key = chr(keycode)
            #print key
            if self.flag == 'no-alpha' and key in string.letters:
                return
            if self.flag == 'no-digit' and key in string.digits:
                return
        event.Skip()


# helper function to get setting from CFG file using ConfigParser
def ConfigSectionMap(section, Config):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if (dict1[option] == -1):
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s:" % option)
            dict1[option] = None
    return dict1


def build_msag_ecode():
    """
    Build MSAG SO error code
    """
    m_ecode = {}

    m_ecode[0] = "No Errors"
    m_ecode[205] = "Invalid PSAP"
    m_ecode[450] = "Batch processes resulted in stranded ANIs"
    m_ecode[410] = "High or Low Range does not match Parity"
    m_ecode[407] = "Change would strand ANIs"
    m_ecode[411] = "Parity Split would strand ANIs"
    m_ecode[404] = "Insert would cause overlap"
    m_ecode[403] = "Change would cause overlap"
    m_ecode[423] = "Join Failed"
    m_ecode[406] = "Split would strand ANIs"
    m_ecode[420] = "Street name not valid"
    m_ecode[416] = "Split Failed"
    m_ecode[418] = "Invalid Function Code"
    m_ecode[409] = "High Range is less than Low Range"
    m_ecode[405] = "ESNs, Street, or Community do not match on join"
    m_ecode[413] = "ESN does not exist"
    m_ecode[408] = "Delete attempted on MSAG with ANIs attached"
    m_ecode[401] = "MSAG does not exist for delete"
    m_ecode[414] = "Invalid Directional"
    m_ecode[451] = "Batch processes resulted in Overlap"
    m_ecode[417] = "Invalid Parity Code"
    m_ecode[422] = "Community Name Not Valid"
    m_ecode[419] = "Function Code Not Supported By Service Order Processing"
    m_ecode[421] = "Street Suffix Not Valid"
    m_ecode[415] = "Invalid Suffix"
    m_ecode[402] = "MSAG already exists"
    m_ecode[412] = "Community does not exist"
    m_ecode[400] = "MSAG does not exist for change"
    m_ecode[0] = "No Errors"
    return m_ecode


def get_msag_e_desc(m_ecode, errdict):
    """
    obtain error description, providing error code
    Usage:    dict = build_msag_ecode()
              desc = get_msag_e_desc(int('412'), dict)
    """
    desc = itemgetter(int(m_ecode))(errdict)
    return desc


def build_ecode():
    """
    Build ALI SO error code dictionary
    """
    # errcode dictionary
    errcode = {}

    errcode[0] = "No Errors"
    errcode[2] = "Non-numeric character in the telephone number."
    errcode[3] = "Non-numeric character in the main telephone number."
    errcode[9] = "Illegal Class of Service"
    errcode[10] = "Illegal Type of Service"
    errcode[103] = "MSAG Not Valid"
    errcode[104] = "House Number Not Valid"
    errcode[105] = "Directional  Not Valid"
    errcode[106] = "Street Name  Not Valid"
    errcode[107] = "Community Name Not Valid"
    errcode[108] = "Exchange Matching Failed"
    errcode[109] = "Company ID Not Valid"
    errcode[110] = "House Number Suffix Not Valid"
    errcode[112] = "Customer Code Not Valid"
    errcode[113] = "NPA_NNX Not Valid"
    errcode[117] = "Low house number is greater than the high house number."
    errcode[118] = "Community name field not populated."
    errcode[119] = "Non-numeric character in ESN or blank ESN."
    errcode[120] = "Community Not Found UsingExchangeField"
    errcode[121] = "Function of Change Code not supported by Service Order Processing"
    errcode[202] = "Record Does Not Exist For A Delete"
    errcode[203] = "Customer Code Does Not Match"
    errcode[247] = "Record Already Exists Under Different Company ID"
    errcode[255] = "Max Reprocessing attempted on Migrates for Non-Existent TN"
    errcode[301] = "Multiple Migrate Reprocessing Attempts Failed"
    errcode[307] = "Company IDs Do Not Match On Error Delete"
    errcode[309] = "Record Exists With Company ID Mismatch"
    errcode[310] = "Unlock Failed -  Main Account Has Sublines"
    errcode[311] = "Lock Exceeds Number Of Retries"
    errcode[312] = "MSAG Update Cause Of TN Error"
    errcode[314] = "TN And Main Account Mismatch"
    errcode[315] = "Change Failed - Completion Date Conflict With Disconnect File"
    errcode[316] = "Record In Disconnect With Greater Complete Date"
    errcode[317] = "Delete Failed - Record In TN Database Has Same Completion Date"
    errcode[321] = "(P)ilot Delete attempted on a subsidiary line."
    errcode[322] = "Function of change (F)inal would result in a pilot delete."
    errcode[323] = "FOC other than (I)nsert attempted during an initial load."
    errcode[601] = "Address not in GIS sites"
    errcode[602] = "Address not in GIS road ranges"
    errcode[603] = "Address not in GIS sites and/or road ranges"
    errcode[651] = "Address not in GIS sites after reprocessing"
    errcode[652] = "Address not in GIS road ranges after reprocessing"
    errcode[653] = "Address not in GIS sites and/or road ranges after reprocessing"
    errcode[700] = "Illegal Function Code"
    errcode[701] = "No MSAG record found."
    errcode[702] = "Record Already Exists"
    errcode[705] = "Record does not exist on a pilot delete."
    errcode[710] = "Customer codes do not match on a change."
    errcode[711] = "Customer codes do not match on a delete."
    errcode[712] = "Record Does Not Exist For A Change"
    errcode[739] = "Street Name Does Not Match On Delete"
    errcode[740] = "Delete attempted on a number with subsidiaries."
    errcode[762] = "Unlock attempted on an unlocked TN (different company ID) ."
    errcode[764] = "Insert Attempted On A TN That Is Unlocked"
    errcode[765] = "Change Attempted On A TN That Is Unlocked"
    errcode[766] = "Delete Attempted On A TN That Is Unlocked"
    errcode[767] = "Company IDs Do Not Match On A Change"
    errcode[768] = "Company IDs Do Not Match On A Delete"
    errcode[769] = "Clerical and ERROR record Company IDs do not match."
    errcode[770] = "Clerical and TN record Company IDs do not match."
    errcode[771] = "Unlock Attempted On A Non-Existent TN"
    errcode[772] = "Company IDs Do Not Match On Unlock"
    errcode[773] = "Migrate Attempted On A Non-Existent TN"
    errcode[774] = "Multiple MSAG matches found"
    errcode[819] = "Subsidiary line unchanged"
    errcode[825] = "Location comment flag set on a change."
    errcode[826] = "Location comment flag set on a migrate to an external company."
    errcode[827] = "Customer Name Change on a Private TN"
    errcode[828] = "Deletion of a Private TN"
    errcode[833] = "Location comment flag set on a delete."
    errcode[863] = "Migrate attempted on a TN that has not been unlocked."
    return errcode

def get_e_desc(ecode, errdict):
    """
    obtain error description, providing error code
    Usage:    dict = build_ecode()
              desc = get_e_desc(int('107'), dict)
    """
    desc = itemgetter(int(ecode))(errdict)
    return desc

def display_msg(msg, title):
    """
    Usage: SO_utils.display_msg('Info message','General')
    """
    dlg = wx.MessageDialog(None, msg, title, wx.OK | wx.ICON_INFORMATION)           
    dlg.ShowModal()
    dlg.Destroy()

    
def ReportLine(Title1, Text1, Title2, Text2, Title3, Text3):
    part1 = '{0: >10}'.format(Title1) + ' = ' + '{0: >0}'.format(Text1) + '\n'
    part2 = '{0: >10}'.format(Title2) + ' = ' + '{0: >0}'.format(Text2) + '\n'
    part3 = '{0: <10}'.format(Title3) + ' =  ' + str(Text3) + '\n'

    writeline = part1 + part2 + part3 + '\n'
    return writeline


def printcenterbox(sentence):    
    screen_width = 120
    text_width = len(sentence) + 5
    box_width = text_width + 4
    left_margin = (screen_width - box_width) / 2
    print ""
    print (' ' * left_margin + '+' + '-' * (box_width + 2) + '+')
    print (' ' * left_margin + '| ' + ' ' * (text_width + 6) + ' |')
    print (' ' * left_margin + '| ' + sentence + ' |')
    print (' ' * left_margin + '| ' + ' ' * (text_width + 6) + ' |')
    print (' ' * left_margin + '+' + '-' * (box_width + 2) + '+')
    print ""

def file_writecenterbox(f1, sentence):    
    screen_width = 120
    text_width = len(sentence)
    box_width = text_width + 4
    left_margin = (screen_width - box_width) / 2

    line1 = ' ' * left_margin + '+' + '-' * (box_width + 1) + '+' +'\n'
    line2 = ' ' * left_margin + '| ' + ' ' * (text_width + 33)  + ' |'+'\n'
    line3 = ' ' * left_margin + '| ' + sentence + ' |'+'\n'
    line4 = ' ' * left_margin + '| ' + ' ' * (text_width + 33) + ' |'+'\n'
    line5 = ' ' * left_margin + '+' + '-' * (box_width + 1) + '+'+'\n'

    f1.write("\n")
    f1.write(line1)
    f1.write(line2)
    f1.write(line3)
    f1.write(line4)
    f1.write(line5)
    f1.write("\n")


def get_list_filenames_filter_file_extensions(extension_list):
    """
    extension_list = ['cfg','CFG']
    Usage:  filename_list = get_list_filenames_filter_file_extensions(extension_list)
    """
    filenames_list = []
    filenames_list = [fn for fn in os.listdir(os.getcwd()) if any([fn.endswith(ext) for ext in extension_list])]
    return filenames_list


def get_filenames_filter_startswith_and_extensions(prefixed, extension_list):
    """
    extension_list = ['cfg','CFG']
    prefixed = "M_"
    Usage:  filename_list = get_filenames_filter_startswith_and_extensions(prefixed, extension_list)
    """

    filenames_list = []
    filenames_list = [fn for fn in os.listdir(os.getcwd()) if (any([fn.endswith(ext) for ext in extension_list])) and (fn.startswith(prefixed))]
    return filenames_list


def select_multi_files_with_prefix_and_extension(prefixed, extension_list):
     """
     Usage:     
     extension_list = ['cfg', 'CFG']
     prefix = 'A_'
     filelist = select_files_with_prefix_and_extension(prefix, extension_list)

     sel_list, listfiles = filelist     
     """
     try:
         dirdlg = wx.DirDialog(None, "Choose a directory:",style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
         if dirdlg.ShowModal() == wx.ID_OK:
                selectedpath =  dirdlg.GetPath()
         dirdlg.Destroy()

         filenames_list = []
         filenames_list = [fn for fn in os.listdir(selectedpath) if (any([fn.endswith(ext) for ext in extension_list])) and (fn.startswith(prefixed))]      

         dlg = wx.MultiChoiceDialog( None, 
                                   "Select one or many files on the list",
                                   "Listing of available files with prefix %s and extensions %s" % (prefixed, extension_list), filenames_list)

         if (dlg.ShowModal() == wx.ID_OK):
                selections = dlg.GetSelections()
                selected_list = [filenames_list[x] for x in selections]           
            
                listfilenames = []
                for item in selected_list:
                    listfilenames.append(item.split('.')[0])
                dlg.Destroy()
            
         return selectedpath, selected_list, listfilenames

     except:
         print "Exception on select_multi_files_with_prefix_and_extension"


def select_single_file_with_prefix_and_extension(prefixed, extension_list):
     """
     Usage:     
     extension_list = ['cfg', 'CFG']
     prefix = 'A_'
     selectedfile = select_single_file_with_prefix_and_extension(prefix, extension_list)    
     """
     try:
         dirdlg = wx.DirDialog(None, "Choose a directory:",style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
         if dirdlg.ShowModal() == wx.ID_OK:
                selectedpath =  dirdlg.GetPath()
         dirdlg.Destroy()

         filenames_list = []
         filenames_list = [fn for fn in os.listdir(selectedpath) if (any([fn.endswith(ext) for ext in extension_list])) and (fn.startswith(prefixed))]      

         sdlg = wx.SingleChoiceDialog( None,
                                            "Select a file from the list",
                                            "Listing of available files with prefix %s and extensions %s" % (prefixed, extension_list), filenames_list, wx.CHOICEDLG_STYLE)
         if (sdlg.ShowModal() == wx.ID_OK):
                selectedfile = sdlg.GetStringSelection()            
                sdlg.Destroy()
    
         return selectedpath, selectedfile

     except:
         print "Exception on select_single_file_with_prefix_and_extension"


def get_latest_file_same_extension(dirpath, fileprefix, extension):
    """
    Usage: fname = wx_utils.get_latest_file_same_extension('/TEST/','169001','sta')
    """
    # remove anything from the list that is not a file (directories, symlinks)
    # the requirement was a list 
    # of files (presumably not including directories)
    # directory sorted by modified time or creation date

    files = filter(os.path.isfile, glob.glob(dirpath + fileprefix+'*.' + extension +'*'))
    
    #files.sort(key=lambda x: os.path.getmtime(x))   #sorted on modified date
    files.sort(key=lambda x: os.path.getctime(x))    #sorted on creation date 
    
    # split the latest file of creation date and just get the filename part
    length = len(files)
    temp = files[length - 1]
    fname = temp.split('\\')[1]

    return fname    


def sort_dir_date_filename(dirpath, mtime):
    """
    #dirpath = "C:/TEST/"
    Usage:  sorted_mtime = sort_dir_date_filename(dirpath, ST_MTIME)
    returns list of sorted filename on dirpath and modified date
    For creation time: sorted_ctime = sort_dir_date_filename(dirpath, ST_CTIME)
    """
    #path to the directory (relative or absolute)
    #dirpath = sys.argv[1] if len(sys.argv) == 2 else r'.'    

    # get all entries in the directory w/ stats
    entries = (os.path.join(dirpath, fn) for fn in os.listdir(dirpath))
    entries = ((os.stat(path), path) for path in entries)
    
    #NOTE: on Windows `ST_CTIME` is a creation date 
    #  but on Unix it could be something else
    #NOTE: use `ST_MTIME` to sort by a modification date

    # leave only regular files, insert creation date
    entries = ((stat[mtime], path)
               for stat, path in entries if S_ISREG(stat[ST_MODE]))

    sorted_list = []

    for cdate, path in sorted(entries):
        #returns sorted list of creation time (time.ctime(cdate)) and filename
        #print time.ctime(cdate), os.path.basename(path)
        
        # returns sorted list of filename
        sorted_list.append(os.path.basename(path))
        
    return sorted_list


##import threading
##   show message box, stay for a while then disappear
##
##msgbox = wx.MessageBox('Hey user, there is something I want to tell you!', 
##                       'Alert', wx.ICON_EXCLAMATION | wx.STAY_ON_TOP)
##msgbox.ShowModal()
##threading.Timer(10.0, msgbox.EndModal).start()


def MsgBox(prompt, message):
    return wx.MessageBox(prompt, message, wx.STAY_ON_TOP)

def textentry(prompt, message):
    """
    TextEntryDialog(parent, message, caption=GetTextFromUserPromptStr,
                    value="", style=TextEntryDialogStyle, pos=DefaultPosition)
                    
    dlg = wx.TextEntryDialog(self, 'Rules:', 'Edit rules', 
                      style=wx.TE_MULTILINE|wx.OK|wx.CANCEL|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
    """    
    dlg = wx.TextEntryDialog(None, prompt, message, "", style=wx.OK|wx.CANCEL)    
    if dlg.ShowModal() == wx.ID_OK:
         val = dlg.GetValue()         
         if val != '':
            return val
         else:
            return ''
    else:    
       return 'NONE'
    dlg.Destroy()
    
def isEven(number):
    return (int(number) % 2 == 0)

def get_date():
    """
    validate date input DD/MM/YYYY format
    Usage: year, month, day = get_date()
    """
    while True:
        date = raw_input("Please enter a date in DD/MM/YYYY format: ")
        try:
            parsed = time.strptime(date, "%d/%m/%Y")
        except ValueError as e:
            MsgBox("Could not parse date: {0}".format(e),'Exception Error')
        else:
            return parsed[:3]


def create_dir(path):
    """
    create directory with provides 'path'
    """
    try:
        os.makedirs(path)
        return True
    except:
        return False

def create_file(target_dir, target_file):
    """
    create target_file in target_dir
    """
    try:
        target = "%s\\%s" % (target_dir, target_file)
        open(target, 'w')
        
    except:
        return False

def check_input(low, high):
    """
    check the input to be an integer between given limits
    Usage: num_test = check_input(1, 50)
    """
    prompt = "Enter an integer number between %d and %d: " % (low, high)
    while True:
        try:
            a = int(raw_input(prompt))
            if low <= a <= high:
                return a
        except ValueError:
            MsgBox("Please input integer number!",'Exception Error')

            
def get_julianday():
    """
    calculate Julian day based on current date time
    import datetime
    i = datetime.datetime.now()
    i.year = 2015
    i.month = 6
    i.day = 24
    """
    try:
        i = datetime.datetime.now()
        sday = str(i.day)
        syear = str(i.year)
        smonth = str(i.month)

        #adjust the month and day string
        tmp = ''
        if len(smonth) == 1:
            tmp += '0' + smonth
            smonth = tmp
            
        tmp = ''
        if len(sday) == 1:
            tmp += '0' + sday
            sday = tmp
            
        fmt = '%Y.%m.%d'
        ss = syear + '.' + smonth + '.' + sday
        
        #dt = datetime.datetime(2015, 6, 24, 0, 0)
        #tt.tm_yday = 175
        
        dt = datetime.datetime.strptime(ss, fmt)     
        tt = dt.timetuple()
        return tt.tm_yday
    
    except:
        #MsgBox("sday = %s   smonth = %s   syear = %s\n\r" % (sday, smonth, syear),'Exception Error')
        return 0


def get_cfgfile():
    """
    Usage: cfg_file = get_cfgfile()
    """       
    prompt = "Enter config file name: "
    while True:
        try:
            s = textentry(prompt,'')

            if s == 'NONE':
                return s
            
            if IsValidCfgFile(s):
                return s
            else:
                MsgBox("example of valid config file name: 11234.cfg....\n\r","Invalid config file name")
                return ''
            
        except ValueError as e:
            MsgBox("Exception get_cfgfile %s " % e,'Exception Error')
            return ''
        
def IsValidCfgFile(s):
    #iscfgfile = re.compile('^[a-zA-Z0-9_-]+\.[cfgCFG$]')
    iscfgfile = re.compile('^[a-zA-Z0-9_-]+\.cfg$')

    if iscfgfile.match(s) >= 0:
        return True
    else:
        return False

def get_datfile():
    """
    Usage: dat_file = get_datfile()
    """       
    prompt = "Enter data file name: " 
    while True:
        try:
            s = textentry(prompt,'')
            if IsValidDatFile(s):
                 return s
            else:
                MsgBox("example of valid dat file name: 171001.dat, 171002.dat...\n\r","Invalid dat file name")
                return ''                
        except ValueError as e:
            MsgBox("Exception get_datfile %s " % e,'Exception Error')
            return ''

def IsValidDatFile(s):
    isdatfile = re.compile('^[0-9]+\.dat$')
    if isdatfile.match(s) >= 0:
        return True
    else:
        return False


def IsValidCompanyID(s):
    isCompanyID = re.compile(r"[^A-Z0-9]")
    result = isCompanyID.sub("",s)           # replace invalid characters to ""
    if result != '':
        return result
    else:
        return ''
    
def IsCompanyID(s):
    isCompanyID = re.compile('^[A-Z0-9]')
    if isCompanyID.match(s) >= 0:
        return True
    else:
        return False

def IsMSAGdat(s):
    isMSAGdat = re.compile('DMSAG[0-9]+\.dat$')
    fname = s.split('.')
    len_fname = len(fname[0])
    if (isMSAGdat.match(s) >= 0) and (len_fname == 11):
        return True
    else:
        return False

def IsMSAGcfg(s):
    isMSAGcfg = re.compile('^M_[A-Z_0-9]+\.cfg$')
    if isMSAGcfg.match(s) >= 0:
        return True
    else:
        return False

def IsALIcfg(s):
    isALIcfg = re.compile('^A_[A-Z_0-9]+\.cfg$')
    if isALIcfg.match(s) >= 0:
        return True
    else:
        return False

def get_listcfgfilenames():
    """
    Usage: listcfgfilenames = get_listcfgfilenames()
    """       
    prompt = "Enter list of config file names separated by comma: "
    """
    This will match anything that is not in the alphanumeric ranges or a hyphen. It also matches the underscore
    """
    r = re.compile(r"[^a-zA-Z0-9-_&,]")       # use a negated character class
    while True:
        try:
            s = textentry(prompt,'')
            """
            s      = "abc_123, 3$45%6_bb, ###$789, 1111"
            result = "abc_123,3456_bb,789,1111"
            """
            result = r.sub("",s)              # replace invalid characters to ""

            if s == 'NONE':
                return s
            
            if result != '':
                return result
            else:
                return ''
            
        except ValueError as e:
            MsgBox("Exception get_listcfgfilenames %s " % e,'Exception Error')
            return ''

def get_provider():
    """
    Usage: provider = get_provider()
    provider name could contain _ , & , space
    """       
    prompt = "Enter provider name: "
    isprovider = re.compile('[A-Z][& _]*')
    while True:
        try:
            s = textentry(prompt,'')
            if isprovider.match(s) >= 0:
                 return s
            else:
                MsgBox("example of valid provider: AT&T, ELIOTT_SEATTLE ...\n\r","Invalid provider name")
                return ''
            
        except ValueError as e:
            MsgBox("Exception get_provider %s " % e,'Exception Error')
            return ''

def get_process_error(prompt):
    """
    Usage: e_process_error = get_process_error()
    process error could contain _ , & , space
    """       
    process_error = re.compile('[A-Z][& _]*')
    while True:
        try:
            s = textentry(prompt,'')
            if process_error.match(s) >= 0:
                 return s
            else:
                return ''
            
        except ValueError as e:
            MsgBox("Exception get_process_error %s " % e,'Exception Error')
            return ''

        
def get_location(prompt):
    """
    Usage: location = get_location(prompt)
    """       
    islocation = re.compile('[A-Z][& _]*')
    while True:
        try:
            s = textentry(prompt,'')
            if islocation.match(s) >= 0:
                 return s
            else:
                MsgBox("example of valid location: ECDWILLIAMSON, ECDOVERTON_PICKETT ...\n\r","Invalid location")
                return ''                
        except ValueError as e:
            MsgBox("Exception get_location %s " % e,'Exception Error')
            return ''

def get_parentdrive():
    """
    Usage: parentdrive = get_parentdrive()
    """       
    prompt = "Enter parent drive (in format <Drive><:>) :  "
    isparentdrive = re.compile('^[A-Z]:')
    while True:
        try:
            s = textentry(prompt,'')
            if isparentdrive.match(s) >= 0:
                 return s
            else:
                MsgBox("example of valid parent drive: C:, D:, W: ....\n\r","Invalid parent drive")
                return ''
            
        except ValueError as e:
            MsgBox("Exception get_parentdrive %s " % e,'Exception Error')
            return ''

def IsValidParentDrive(s):
    isparentdrive = re.compile('^[A-Z]:')
    if isparentdrive.match(s) >= 0:
        return True
    else:
        return False

def get_parentdir():
    """
    Usage: parentdir = get_parentdir()
    """       
    prompt = "Enter parent directory: "
    isparentdir = re.compile('[a-zA-Z]_*')
    while True:
        try:
            s = textentry(prompt,'')
            if isparentdir.match(s) >= 0:
                 return s
            else:
                MsgBox("example of valid parent directory: xALIDBMS_parent ....\n\r","Invalid parent directory")
                return ''
            
        except ValueError as e:
            MsgBox("Exception get_parentdir %s " % e,'Exception Error')
            return ''


def get_insert():
    """
    Usage: insert = get_insert()
    """       
    prompt = "Enter count of insert record: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a


def IsValidNumber(a):
    """
    Usage: number = IsValidNumber(a)
    """       
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a

    

def get_processed():
    """
    Usage: processed = get_processed()
    """       
    prompt = "Enter count of processed record: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a

def get_errors():
    """
    Usage: errors = get_errors()
    """       
    prompt = "Enter count of error record: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a

def get_delete():
    """
    Usage: delete = get_delete()
    """       
    prompt = "Enter count of delete record: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a


def get_changes():
    """
    Usage: changes = get_changes()
    """       
    prompt = "Enter count of changes record: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a

    
def get_waittime():
    """
    Usage: waittime = get_waittime()
    """       
    prompt = "Enter wait time (in sec) for file to process: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a

def get_msag_error_code(prompt):
    """
    Usage: errorcode = get_error_code()
    """       
    validcode = ['000','205','400','401','402','403','405','406','407','408','409','410','411','412','413','414','415','416','417','419','420','421','423','450','451']    
    a=textentry(prompt,'')
    try:
       if a in validcode:
           return a
       else:
           MsgBox("Valid codes are:  %s\n\r" % validcode,"Invalid error code")
           return ''
    except ValueError:
       return ''


def get_error_code(prompt):
    """
    Usage: errorcode = get_error_code()
    """       
    validcode = ['002','003','009','010','103','104','105','106','107','108','109','110','112','113','117','118','119','120','121','202','203','247','255','301','307','309','310','311','312','314','315','316','317','321','322','323','601','602','603','651','652','653','700','701','702','705','710','711','712','739','740','762','764','765','766','767','768','769','770','771','772','773','774','819','825','826','827','828','833','863']    
    a=textentry(prompt,'')
    try:
       if a in validcode:
           return a
       else:
           MsgBox("Valid codes are:  %s\n\r" % validcode,"Invalid error code")
           return ''
    except ValueError:
       return ''

def get_errors_errorcode(prompt):
    """
    Usage: errorcode = get_errors_error_code()
    """       
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a    


def get_autocorrect():
    """
    Usage: autocorrect = get_autocorrect()
    """       
    prompt = "Enter count of auto-correct record: "
    a=textentry(prompt,'')
    try:
        int(a)
    except ValueError:
        try:
            float(a)
        except ValueError:
            a=0
            return a
            
    if a==0:
        a=0
        return a
    else:
        return a


def make_default_ALI_dat_filename():
    juliandate = get_julianday()
    prefix = str(juliandate).zfill(3)                      # pad juliandate with zero
    seqno = "001.dat"
    defaultALIdatfile = prefix + seqno
    return defaultALIdatfile


def make_default_ALI_cfg_filename():
    juliandate = get_julianday()
    prefix = 'A_' + str(juliandate).zfill(3)                # pad juliandate with zero
    seqno = "001_"
    companyID = "ATT.cfg"
    defaultALIcfgfile = prefix + seqno + companyID
    return defaultALIcfgfile


def make_default_MSAG_cfg_filename():
    juliandate = get_julianday()
    prefix = "M_" + str(juliandate).zfill(3)              # pad juliandate with zero
    seqno = "001_"
    username = "DMGR1.cfg"
    defaultMSAGcfgfile = prefix + seqno + username
    return defaultMSAGcfgfile


def make_default_MSAG_dat_filename():
    juliandate = get_julianday()
    prefix = "DMSAG" + str(juliandate).zfill(3)              # pad juliandate with zero
    seqno = "001.dat"
    defaultMSAGdatfile = prefix + seqno
    return defaultMSAGdatfile


def get_files_in_directory(directory="C:\\"):
    """
    Usage: get_files_in_directory(directory="C:\\")
           C:\\myfolderA\\myFolderB\\myFile.MOD
           output: myfolderB
    """
    for root, dirs, files in os.walk(directory, topdown='true'):
        print("root %s dirs %s files %s" %(root, dirs, files));
        for file in files:
            ext = os.path.splitext(file)[-1].lower();
            if (ext == '.mod'):
                print(file);


def get_MSAG_files_and_directories(path):
    """
    Usage:  path = self.edit3.Value + "\\" + self.edit4.Value + "\\" + self.edit6.Value + "\\Providers\\MSAGSO\\"
            listUserName = SO_utils.get_MSAG_files_and_directories(path)
    Output:    DMGR1
               DQA1
    """
    try:
        if os.path.exists(path):
            dirs = os.listdir(path)
            names = []
            # print all the files and directories
            for file in dirs:
                names.append(file)

            return names
    except:
        print "Exception in get_MSAG_files_and_directories"


def get_ALI_files_and_directories(path):
    """
    Usage:  path = self.edit3.Value + "\\" + self.edit4.Value + "\\" + self.edit6.Value + "\\Providers\\"
            listCOI = SO_utils.get_ALI_files_and_directories(path)

    Output:    names = ['MSAGSO', 'Provider5678', 'Provider890', 'ProviderATT']
               CompanyID = ['MSAGSO', 'Provider5678', 'Provider890', 'ProviderATT']
    """
    try:
        if os.path.exists(path):
            dirs = os.listdir(path)
            names = []
            CompanyID = []
            # print all the files and directories
            for file in dirs:
                names.append(file)

            for i in range(0, len(names)):
                # keep the <Provider><COID>
                #CompanyID.append(names[i].lstrip('Provider'))
                CompanyID.append(names[i])

            return CompanyID

    except:
        print "Exception in get_ALI_files_and_directories"


def msag_obtain_expect_result_from_cfgfile(f1, cfg_file, Config, e_results):
    """
    Obtain expected results from CFG file
    """
    filepath = os.getcwd() + "\\"         #directory of current running scripts
    cfgfilepath = filepath + cfg_file

    #write log
    f1.write("Obtain expected results from %s\n" % cfgfilepath)        
    f1.write("\n\r")

    try:            
        Config.read(cfgfilepath)

        e_msagcfg = Config.get('General', 'msagcfg')            
        e_msagdat = Config.get('General', 'msagdat')                        
        e_pdrive = Config.get('General','parentdrive')            
        e_pdir = Config.get('General','parentdir')            
        e_username = Config.get('General','username')
        e_location = Config.get('General', 'location')
        e_maxtimeout = Config.get('General', 'maxtimeout')
                   
        e_processed = Config.get('STA File','processed')

        e_nonprocessed = Config.get('STA File','nonprocessed')

        e_errors = Config.get('STA File','errors')            
        e_inserts = Config.get('STA File','inserts')
        e_deletes = Config.get('STA File','deletes')
        e_befores = Config.get('STA File','befores')
        e_afters = Config.get('STA File','afters')

        e_proc_error = Config.get('PERR File','process_error')

        # obtains [ERROR Type] dictionary
        c_err_code = ConfigSectionMap("ERROR Type", Config)
                
        e_results.append(e_msagcfg)         # [0] = msag cfg
        e_results.append(e_msagdat)         # [1] = msag dat
        e_results.append(e_pdrive)          # [2] = parent drive
        e_results.append(e_pdir)            # [3] = parent dir
        e_results.append(e_username)        # [4] = user name
        e_results.append(e_location)        # [5] = location
        e_results.append(e_maxtimeout)      # [6] = max time out
        
        e_results.append(e_processed)       # [7] = processed

        e_results.append(e_nonprocessed)    # [8] = nonprocessed

        e_results.append(e_errors)          # [9] = errors
        e_results.append(e_inserts)         # [10] = inserts
        e_results.append(e_deletes)         # [11] = deletes
        e_results.append(e_befores)         # [12] = befores
        e_results.append(e_afters)          # [13] = afters
        
        e_results.append(e_proc_error)      # [14] = Expected processing error

        #write log
        f1.write("From  %s:\n\r" % cfg_file)
        f1.write("msagcfg  = %s\n" % e_results[0])
        f1.write("msagdat  = %s\n" % e_results[1])
        f1.write("parent drive  = %s\n" % e_results[2])
        f1.write("parent directory   = %s\n" % e_results[3])
        f1.write("username   = %s\n" % e_results[4])
        f1.write("provider's location   = %s\n" % e_results[5])
        f1.write("max timeout   = %s\n" % e_results[6])
        f1.write("expected processed   = %s\n" % e_results[7])
        f1.write("expected non-processed   = %s\n" % e_results[8])
                    
        f1.write("expected errors  = %s\n" % e_results[9])
        f1.write("expected inserts   = %s\n" % e_results[10])
        f1.write("expected deletes  = %s\n" % e_results[11])
        f1.write("expected befores  = %s\n" % e_results[12])
        f1.write("expected afters  = %s\n" % e_results[13])
        f1.write("expected processing error  = %s\n\r" % e_results[14])
        f1.write("ERROR Type  = %s\n\r" % c_err_code)
                                        
        return (True, c_err_code)
        
    except:
        #MsgBox("Read CFG file exception\n\r",'Exception Error')
        f1.write("Read CFG file exception\n")
        return False


def obtain_expect_result_from_cfgfile(f1, cfg_file, Config, e_results):
    """
    Obtain expected results from CFG file
    """
    filepath = os.getcwd() + "\\"         #directory of current running scripts
    cfgfilepath = filepath + cfg_file

    #write log
    f1.write("Obtain expected results from %s\n" % cfgfilepath)        
    f1.write("\n\r")

    try:            
        Config.read(cfgfilepath)

        e_datfile = Config.get('General', 'datfile')            
        e_companyID = Config.get('General', 'companyid')            
        e_location = Config.get('General', 'location')            
        e_pdrive = Config.get('General','parentdrive')            
        e_pdir = Config.get('General','parentdir')            
        e_waittime = Config.get('General','waittime')
        
        e_insert = Config.get('STA File','inserts')            
        e_processed = Config.get('STA File','processed')            
        e_errors = Config.get('STA File','errors')            
        e_delete = Config.get('STA File','delete')
        e_changes = Config.get('STA File','changes')
        e_autocorr = Config.get('STA File','autocorrect')
        e_migrate = Config.get('STA File','migrate')
        e_unlock = Config.get('STA File','unlock')
        e_pilotdeletes = Config.get('STA File','pilotdeletes')
        
        e_proc_error = Config.get('PERR File','process_error')
        e_queue_error = Config.get('QERR File','queue_error')

        c_err_code = {}
        c_autocorr_err_code = {}
        c_migrate_err_code = {}

        # obtains [ERROR Type] dictionary
        c_err_code = ConfigSectionMap("ERROR Type", Config)

        # obtains [AUTOCORR] dictionary
        c_autocorr_err_code = ConfigSectionMap("AUTOCORR", Config)

        # obtains [MERROR Type] dictionary
        c_migrate_err_code = ConfigSectionMap("MERROR Type", Config)
        
        e_results.append(e_datfile)                  #[0] = dat file
        e_results.append(e_companyID)                #[1] = company ID
        e_results.append(e_location)                 #[2] = location
        e_results.append(e_pdrive)                   #[3] = parent drive
        e_results.append(e_pdir)                     #[4] = parent directory
        e_results.append(e_waittime)                 #[5] = max time-out
        
        e_results.append(e_insert)                   #[6] = insert
        e_results.append(e_processed)                #[7] = processed
        e_results.append(e_errors)                   #[8] = error
        e_results.append(e_delete)                   #[9] = delete
        e_results.append(e_changes)                  #[10] = change
        
        e_results.append(e_autocorr)                 #[11] = autocor
        e_results.append(e_proc_error)               #[12] = expected process error
        e_results.append(e_migrate)                  #[13] = migrate

        e_results.append(e_unlock)                   #[14] = unlock
        e_results.append(e_pilotdeletes)             #[15] = pilot deletes
        e_results.append(e_queue_error)              #[16] = expected queue error

        #write log
        Log_Starting_Process("PUTTING INFO INTO E_RESULTS:\n", f1)
        f1.write("datfile   = %s\n" % e_results[0])
        f1.write("companyID  = %s\n" % e_results[1])
        f1.write("location  = %s\n" % e_results[2])
        f1.write("parent drive  = %s\n" % e_results[3])
        f1.write("parent directory  = %s\n" % e_results[4])
        f1.write("max time-out  = %s\n" % e_results[5])
        f1.write("\n\r")            
        f1.write("expected inserts   = %s\n" % e_results[6])
        f1.write("expected processed   = %s\n" % e_results[7])
        f1.write("expected error   = %s\n" % e_results[8])
        f1.write("expected delete   = %s\n" % e_results[9])
        f1.write("expected changes   = %s\n" % e_results[10])
        f1.write("expected autocorrect  = %s\n" % e_results[11])        
        f1.write("expected process error  = %s\n" % e_results[12])        
        f1.write("expected migrate  = %s\n" % e_results[13])
        f1.write("expected unlock   = %s\n" % e_results[14])
        f1.write("expected pilot delete  = %s\n" % e_results[15])
        f1.write("expected queue error  = %s\n\r" % e_results[16])
        f1.write("From  %s  file:\n" % cfg_file)
        f1.write("ERROR Type  = %s\n" % c_err_code)
        f1.write("AUTOCORR  = %s\n" % c_autocorr_err_code)
        f1.write("MERROR Type  = %s\n\r" % c_migrate_err_code)
                       
        if e_results[12] != '':
            f1.write("expected process error     = %s\n" % e_results[12])

        if e_results[16] != '':
            f1.write("expected queue error     = %s\n" % e_results[16])
                       
        return (True, c_err_code, c_autocorr_err_code, c_migrate_err_code)
        
    except:
        f1.write("Read CFG file exception\n")
        return False


def copy_dat_file_to_process(e_results, f1, mapdrive):
    """
    Copy dat file from source to destination
    e_results[0] =  dat file
    e_results[3] =  parent drive letter with colon (:)
    e_results[4] =  parent directory
    e_results[2] =  location
    e_results[1] =  company ID - <COID>  ( aka provider name)    
    """
    filepath = os.getcwd() + '\\'
    source = filepath + e_results[0]

    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:" + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"


    try:
        # do not do this because many existing files on the parent directory will be lost
        #if os.path.exists(dest):
        #    # dest exists
        #    f1.write("\n\r")
        #    f1.write("dest = %s\n\r" % dest)
        #    f1.write("\n\r")
        #else:
        #    createdest = create_dir(dest)
        #    if createdest:
        #        f1.write("\n\r")
        #        f1.write("%s is created successfully\n\r" % dest)
        #        f1.write("\n\r")

        #dest = C:\Intrepid_Admin_SOI_Files\TUAN\Providers\Provider890
            
        if os.path.exists(source):        
            #write log
            Log_Starting_Process("COPYING DAT FILE TO PROCESS DIRECTORY:", f1)
            f1.write("Copying dat file %s\n\r" % e_results[0])
            f1.write("Parent directory = %s - Location = %s - Provider = %s\n\r" % (e_results[3] + "\\" + e_results[4], e_results[2], e_results[1]))
            f1.write("Copy %s  from directory %s\n\r" % (e_results[0], source))
            f1.write("              to directory %s\n\r" % dest)
                        
            try:
                if os.path.exists(dest):
                    #copy file from source path to destination path using shutil
                    shutil.copy(source, dest)
                
                    #write log
                    f1.write("Copying file done\n")
                    return True

                else:
                    f1.write("Provider%s   not exists in %s\n" % (e_results[1], dest))
                    f1.write("Provider%s   not exists in %s\n" % (e_results[1], dest))
                    return False
                                
            except ValueError as e:
                f1.write("Copy file exception = %s" % e)

            
        else:
            f1.write("%s  not exists in %s\n" % (e_results[0], source))
            return False
            
    except:
        #MsgBox("Read dat file exception.  %s   not exists in  %s\n\r" % (e_results[0], source),'Exception Error')
        f1.write("%s  not exists in %s\n" % (e_results[0], source))
        return False


def count_errorcode_on_list(err_list):
    """
    Count of error code in a list
    errlist = ['100','201','100','201','209','209','201','209','209','209'] 
    
    Usage: err_dict = SO_utils.count_errorcode_on_list(errlist)
    Output: err_dict = {'201': '3', '209': '5', '100': '2'}
    """
    
    # initialize err_dict dictionary
    err_dict = {}
    
    idx = 0
    count = 1

    # need to sort the list first
    err_list.sort()

    while (idx + 1 < len(err_list)):
        if (err_list[idx] == err_list[idx + 1]):
            count = count + 1
            idx = idx + 1
        else:
            err_dict.update( {err_list[idx]:str(count)} )            
            count = 1
            idx = idx + 1
   
    err_dict.update( {err_list[idx]:str(count)} )    
    return err_dict


def migrate_MSTA_MERR_process(e_results, f1, ecode, cfg_err_code, mapdrive):
    #obtain actual results from MSTA files
    a_msta_results = []
    e_msta_results = []
    verifyMSTA = obtain_actual_result_from_MSTA_files(a_msta_results, f1, e_msta_results, e_results, mapdrive) 
        
    if verifyMSTA:
        #obtain error code from MERR file
        merr_err_code = []
        verifyMERRfile = obtain_error_codes_from_MERR_file(e_results, f1, merr_err_code, ecode, mapdrive)
        verifyMERR, cnt_merrorcode = verifyMERRfile

        if verifyMERR:
            #verify error code from MSTA file
            a_msta_err_code = []   #list of actual result error count and error code in MSTA file
            verifyMSTA = verify_error_code_in_MSTA_file(a_msta_results, a_msta_err_code, e_results, f1, ecode, mapdrive)

            verifyErrorCodeFromMSTA, cnt_msta_errorcode = verifyMSTA

            if verifyErrorCodeFromMSTA:

                #verify other info 
                #compare count of migrate records
                if int(e_results[13]) == int(a_msta_results[9]):
                    pass0 = True
                else:
                    pass0 = False
                
                #verify other info 
                #compare count of insert records
                if int(e_results[6]) == int(a_msta_results[3]):
                    pass1 = True
                else:
                    pass1 = False
                
                #compare count of processed record   
                if int(e_results[7]) == int(a_msta_results[4]):
                    pass2 = True
                else:
                    pass2 = False
                
                #compare count of error record
                if int(e_results[8]) == int(a_msta_results[5]):
                      i = 0
                      for ecode in a_msta_err_code:
                          if a_msta_err_code[i] in merr_err_code:
                              pass3 = True
                          else:
                              pass3 = False
                          i = i + 1
                else:
                    pass3 = False
                    
                # compare count of delete record
                if int(e_results[9]) == int(a_msta_results[6]):
                    pass4 = True
                else:
                    pass4 = False

                # compare count of changes record
                if int(e_results[10]) == int(a_msta_results[7]):
                    pass5 = True
                else:
                    pass5 = False 

                #verify expected results and actual results
                #f1.write("Expected migrate        = %s        -  Actual migrate         = %s   -  pass0 = %s\n\r" % (e_results[13], a_msta_results[9], pass0))
                #f1.write("Expected inserts          = %s        -  Actual inserts           = %s   -  pass1 = %s\n\r" % (e_results[6], a_msta_results[3], pass1))
                #f1.write("Expected processed     = %s        -  Actual processed     = %s   -  pass2 = %s\n\r" % (e_results[7], a_msta_results[4], pass2))
                #f1.write("Expected errors            = %s        -  Actual errors             = %s   -  pass3 = %s\n\r" % (e_results[8], a_msta_results[5], pass3))
                #f1.write("Expected deletes          = %s        -  Actual deletes         = %s   -  pass4 = %s\n\r" % (e_results[9], a_msta_results[6], pass4))
                #f1.write("Expected changes       = %s        -  Actual changes        = %s   -  pass5 = %s\n\r" % (e_results[10], a_msta_results[7], pass5))

                f1.write(ReportLine("Expected migrate", e_results[13], "Actual migrate", a_msta_results[9], "pass0", pass0))
                f1.write(ReportLine("Expected inserts", e_results[6], "Actual inserts", a_msta_results[3], "pass1", pass1))
                f1.write(ReportLine("Expected processed", e_results[7], "Actual processed", a_msta_results[4], "pass2", pass2))
                f1.write(ReportLine("Expected errors", e_results[8], "Actual errors", a_msta_results[5], "pass3", pass3))
                f1.write(ReportLine("Expected deletes", e_results[9], "Actual deletes", a_msta_results[6], "pass4", pass4))
                f1.write(ReportLine("Expected changes", e_results[10], "Actual changes", a_msta_results[7], "pass5", pass5))

                Log_Starting_Process("MIGRATE - VERIFICATION OF EXPECTED ERROR CODE AND COUNT WITH ACTUAL RESULTS", f1)
                pass77 = verify_error_code_in_cfg_with_actual_result(cfg_err_code, cnt_merrorcode, cnt_msta_errorcode, f1)
                pass7a, pass7b = pass77

                pass7 = pass7a and pass7b

                f1.write(ReportLine("Count error code from CFG file", cfg_err_code, "Count error code on MSTA file", cnt_msta_errorcode, "pass7a", pass7a))
                f1.write(ReportLine("Count error code from MERR file", cnt_merrorcode, "Count error code on MSTA file", cnt_msta_errorcode, "pass7b", pass7b))
                f1.write("pass7 = %s\n\r" % pass7)

                autocorrfile = e_results[0].split('.')
                a_autocorrfile = autocorrfile[0] + '.' + 'autocor'

                #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                if os.path.exists(mapdrive + "\\"):
                        dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                else: 
                        dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                AUTOCORfilepath = dest + a_autocorrfile
                
                #Verify if there is AUTOCOR file exists, then obtain the autocorrect from AUTOCOR file.
                try:
                    Log_Starting_Process("MIGRATE - VERIFICATION OF AUTOCOR", f1)
                    if  os.path.exists(AUTOCORfilepath):                       
                        a_autocorrected = obtain_autocorrection(e_results, f1)
                               
                        if a_autocorrected != 0:
                            
                            # compare count of autocorrect record
                            if int(e_results[11]) == int(a_autocorrected):
                                pass7 = True
                            else:
                                pass7 = False

                            f1.write("Expected autocorr      = %s    - From AUTOCOR file: actual autocorr = %s   -  pass7 = %s\n\r" % (e_results[11], a_autocorrected, pass7)) 
                            
                            
                                                   
                        allpass = pass0 and pass1 and pass2 and pass3 and pass4 and pass5 and pass6 and pass7                      
                        # write log
                        f1.write("allpass = %s    (pass0 = %s, pass1 = %s, pass2 = %s, pass3 = %s, pass4 = %s, pass5 = %s, pass6 = %s, pass7 = %s)\n\r" % (allpass,pass0,pass1,pass2,pass3,pass4,pass5,pass6,pass7))
                    
                    else:
                        f1.write("No occurence of  %s   in %s\n\r" % (a_autocorrfile, dest))

                        allpass = pass0 and pass1 and pass2 and pass3 and pass4 and pass5

                        # write log                        
                        f1.write("allpass = %s    (pass0 = %s, pass1 = %s, pass2 = %s, pass3 = %s, pass4 = %s, pass5 = %s)\n\r" % (allpass,pass0,pass1,pass2,pass3,pass4,pass5))
                    
                except:
                    f1.write("Read AUTOCOR file exception.\n\r")
                                                                  
                return allpass


def msag_migrate_MSTA_MERR_process(e_results, f1, ecode, cfg_err_code, mapdrive):
    #obtain actual results from MSTA files
    a_msta_results = []
    e_msta_results = []
    verifyMSTA = msag_obtain_actual_result_from_MSTA_files(a_msta_results, f1, e_msta_results, e_results, mapdrive) 
        
    if verifyMSTA:
        #obtain error code from MERR file
        merr_err_code = []
        verifyMERRfile = msag_obtain_error_codes_from_MERR_file(e_results, f1, merr_err_code, ecode, mapdrive)
        verifyMERR, cnt_merrorcode = verifyMERRfile

        if verifyMERR:
            #verify error code from MSTA file
            a_msta_err_code = []   #list of actual result error count and error code in MSTA file
            verifyMSTA = msag_verify_error_code_in_MSTA_file(a_msta_results, a_msta_err_code, e_results, f1, ecode, mapdrive)

            verifyErrorCodeFromMSTA, cnt_msta_errorcode = verifyMSTA

            if verifyErrorCodeFromMSTA:

                #verify other info 
                #compare count of migrate records
                if int(e_results[13]) == int(a_msta_results[9]):
                    pass0 = True
                else:
                    pass0 = False
                
                #verify other info 
                #compare count of insert records
                if int(e_results[6]) == int(a_msta_results[3]):
                    pass1 = True
                else:
                    pass1 = False
                
                #compare count of processed record   
                if int(e_results[7]) == int(a_msta_results[4]):
                    pass2 = True
                else:
                    pass2 = False
                
                #compare count of error record
                if int(e_results[8]) == int(a_msta_results[5]):
                      i = 0
                      for ecode in a_msta_err_code:
                          if a_msta_err_code[i] in merr_err_code:
                              pass3 = True
                          else:
                              pass3 = False
                          i = i + 1
                else:
                    pass3 = False
                    
                # compare count of delete record
                if int(e_results[9]) == int(a_msta_results[6]):
                    pass4 = True
                else:
                    pass4 = False

                # compare count of changes record
                if int(e_results[10]) == int(a_msta_results[7]):
                    pass5 = True
                else:
                    pass5 = False 

                #verify expected results and actual results
                #f1.write("Expected migrate        = %s        -  Actual migrate         = %s   -  pass0 = %s\n\r" % (e_results[13], a_msta_results[9], pass0))
                #f1.write("Expected inserts          = %s        -  Actual inserts           = %s   -  pass1 = %s\n\r" % (e_results[6], a_msta_results[3], pass1))
                #f1.write("Expected processed     = %s        -  Actual processed     = %s   -  pass2 = %s\n\r" % (e_results[7], a_msta_results[4], pass2))
                #f1.write("Expected errors            = %s        -  Actual errors             = %s   -  pass3 = %s\n\r" % (e_results[8], a_msta_results[5], pass3))
                #f1.write("Expected deletes          = %s        -  Actual deletes         = %s   -  pass4 = %s\n\r" % (e_results[9], a_msta_results[6], pass4))
                #f1.write("Expected changes       = %s        -  Actual changes        = %s   -  pass5 = %s\n\r" % (e_results[10], a_msta_results[7], pass5))

                f1.write(ReportLine("Expected migrate", e_results[13], "Actual migrate", a_msta_results[9], "pass0", pass0))
                f1.write(ReportLine("Expected inserts", e_results[6], "Actual inserts", a_msta_results[3], "pass1", pass1))
                f1.write(ReportLine("Expected processed", e_results[7], "Actual processed", a_msta_results[4], "pass2", pass2))
                f1.write(ReportLine("Expected errors", e_results[8], "Actual errors", a_msta_results[5], "pass3", pass3))
                f1.write(ReportLine("Expected deletes", e_results[9], "Actual deletes", a_msta_results[6], "pass4", pass4))
                f1.write(ReportLine("Expected changes", e_results[10], "Actual changes", a_msta_results[7], "pass5", pass5))

                #c_err_code, c_autocorr_err_code, c_migrate_err_code
                Log_Starting_Process("MIGRATE - VERIFICATION OF EXPECTED ERROR CODE AND COUNT WITH ACTUAL RESULTS", f1)
                pass77 = verify_error_code_in_cfg_with_actual_result(cfg_err_code, cnt_merrorcode, cnt_msta_errorcode, f1)
                pass7a, pass7b = pass77

                pass7 = pass7a and pass7b

                f1.write(ReportLine("Count error code from CFG file", cfg_err_code, "Count error code on MSTA file", cnt_msta_errorcode, "pass7a", pass7a))
                f1.write(ReportLine("Count error code from MERR file", cnt_merrorcode, "Count error code on MSTA file", cnt_msta_errorcode, "pass7b", pass7b))
                f1.write("pass7 = %s\n\r" % pass7)

                autocorrfile = e_results[0].split('.')
                a_autocorrfile = autocorrfile[0] + '.' + 'autocor'

                #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                if os.path.exists(mapdrive + "\\"):
                        dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
                else: 
                        dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

                AUTOCORfilepath = dest + a_autocorrfile
                
                #Verify if there is AUTOCOR file exists, then obtain the autocorrect from AUTOCOR file.
                try:
                    Log_Starting_Process("MIGRATE - VERIFICATION OF AUTOCOR", f1)
                    if  os.path.exists(AUTOCORfilepath):                       
                        a_autocorrected = obtain_autocorrection(e_results, f1)
                               
                        if a_autocorrected != 0:
                            
                            # compare count of autocorrect record
                            if int(e_results[11]) == int(a_autocorrected):
                                pass7 = True
                            else:
                                pass7 = False

                            f1.write("Expected autocorr      = %s    - From AUTOCOR file: actual autocorr = %s   -  pass7 = %s\n\r" % (e_results[11], a_autocorrected, pass7))                            
                                                   
                        allpass = pass0 and pass1 and pass2 and pass3 and pass4 and pass5 and pass6 and pass7                      
                        # write log
                        f1.write("allpass = %s    (pass0 = %s, pass1 = %s, pass2 = %s, pass3 = %s, pass4 = %s, pass5 = %s, pass6 = %s, pass7 = %s)\n\r" % (allpass,pass0,pass1,pass2,pass3,pass4,pass5,pass6,pass7))
                    
                    else:
                        f1.write("No occurence of  %s   in %s\n\r" % (a_autocorrfile, dest))
                        
                        allpass = pass0 and pass1 and pass2 and pass3 and pass4 and pass5

                        # write log                        
                        f1.write("allpass = %s    (pass0 = %s, pass1 = %s, pass2 = %s, pass3 = %s, pass4 = %s, pass5 = %s)\n\r" % (allpass,pass0,pass1,pass2,pass3,pass4,pass5))
                    
                except:
                    #MsgBox("Read AUTOCOR file exception.\n\r",'Exception Error')
                    f1.write("Read AUTOCOR file exception.\n\r")
                                                                  
                return allpass



def msag_copy_dat_file_to_process(e_results, f1, mapdrive):
    """
    Copy dat file from source to destination
    e_results[7] =  msag dat file
    e_results[3] =  parent drive letter with colon (:)
    e_results[4] =  parent directory
    e_results[2] =  location
    e_results[1] =  company ID - <COID>  ( aka provider name) 
    e_results[6] = user name (for MSAG process) 
    """
    filepath = os.getcwd() + '\\'

    source = filepath + e_results[1]        # use msag dat file name

    """
    C:\Intrepid_Admin_SOI_Files\TUAN\Providers\MSAGSO\username
    """
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:" + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    try:
        # do not do this because many existing files on the parent directory will be lost
        #if os.path.exists(dest):
        #    # dest exists
        #    f1.write("\n\r")
        #    f1.write("dest = %s\n\r" % dest)
        #    f1.write("\n\r")
        #else:
        #    createdest = create_dir(dest)
        #    if createdest:
        #        f1.write("\n\r")
        #        f1.write("%s is created successfully\n\r" % dest)
        #        f1.write("\n\r")

        #dest = C:\Intrepid_Admin_SOI_Files\TUAN\Providers\MSAGSO\DMGR1
            
        if os.path.exists(source):        
            #write log
            f1.write("Copying dat file %s\n\r" % e_results[1])
            f1.write("Parent directory = %s - Location = %s - username = %s\n\r" % (e_results[2] + "\\" + e_results[3], e_results[5], e_results[4]))
            f1.write("Copy %s  from directory %s\n\r" % (e_results[1], source))
            f1.write("              to directory %s\n\r" % dest)
                        
            try:
                if os.path.exists(dest):
                    #copy file from source path to destination path using shutil
                    shutil.copy(source, dest)
                
                    #write log
                    f1.write("Copying file done\n")
                    return True
                else:
                    f1.write("User name  %s   not exists in %s\n" % (e_results[4], dest))
                    f1.write("User Name  %s   not exists in %s\n" % (e_results[4], dest))
                    return False
                                
            except ValueError as e:
                f1.write("Copy file exception = %s" % e)
            
        else:
            f1.write("%s  not exists in %s\n\r" % (e_results[1], source))
            return False
            
    except:
        #MsgBox("Read dat file exception.  %s   not exists in  %s\n\r" % (e_results[0], source),'Exception Error')
        f1.write("%s  not exists in %s\n\r" % (e_results[1], source))
        return False

def msag_obtain_actual_result_from_STA_files(a_results, f1, e_results, mapdrive):
    """
    Obtain actual results from MSAG STA files
    """   
    #read STA, ERR, AUTOCOR, PERR files from dest directory        
    stafile = e_results[1].split('.')
    a_stafile = stafile[0] + '.' + 'sta'

    #verify if PERR not exists then do not check for Non-processed records in STA
    a_perrfile = stafile[0] + '.' + 'perr'

##    # file prefix is the file name part of e_results[0]
##    sta_fileprefix = stafile[0]
##    fileextension = 'STA'
##    dirpath = e_results[3] + "/" + e_results[4] + "/" + e_results[2] + "/Providers/Provider" + e_results[1] + "/" + e_results[1] + "/"
##    
##    # sort dest on modified date with same file name and latest extension
##    a_stafile = get_latest_file_same_extension(dirpath, sta_fileprefix, fileextension)
    
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"


##    #write log
##    f1.write("After sort dir, latest sta file selected = %s\n\r" % a_stafile)
##    f1.write("\n\r")
    
    STAfilepath = dest + a_stafile
    
    # Only run when a_stafile exists
    if (os.path.exists(STAfilepath) and IsValid_MSAG_STA(STAfilepath, f1)):
        
        #add to actual results list
        a_results.append(a_stafile)          # [0] = stat file
        a_results.append(e_results[4])       # [1] = username
        a_results.append(e_results[5])       # [2] = location
        
        #write log
        f1.write("Obtain actual results from %s\n\r" % STAfilepath)
        f1.write("dest = %s\n\r" % dest)
                
        try:
            a_notprocessed = ''

            data_file = open(STAfilepath,'r') 
                      
            for line in data_file:

                if re.match("Total Records Processed:(.*)", line):
                    a_processed = line[25:len(line)]

                # obtain count of Not Processed record 
                if re.match("Total Records Not Processed(.*)", line):
                    a_notprocessed = line[46:len(line)]                                 
                                                        
                if re.match("Total Errors:(.*)", line):
                    a_errors = line[14:len(line)]
                    
                if re.match("Inserts:(.*)", line):
                    a_inserts = line[9:len(line)]
                    
                # obtain count of 'Deletes: '
                if re.match("Deletes:(.*)", line):
                    a_deletes = line[9:len(line)]
 
                # obtain count of 'Befores: '
                if re.match("Befores:(.*)", line):
                    a_befores = line[9:len(line)]                                    
                
                # obtain count of Afters record 
                if re.match("Afters:(.*)", line):
                    a_afters = line[8:len(line)]
                    
            data_file.close()

            if (a_notprocessed == ''):
                a_notprocessed = ' 0\n'
            
            # strip all the trailing spaces
            a_processed = a_processed.strip(' ')
            a_processed = a_processed.strip('\n')

            a_notprocessed = a_notprocessed.strip(' ')
            a_notprocessed = a_notprocessed.strip('\n')

            a_errors = a_errors.strip(' ')
            a_errors = a_errors.strip('\n')
            a_inserts = a_inserts.strip(' ')
            a_inserts = a_inserts.strip('\n')
            a_deletes = a_deletes.strip(' ')
            a_deletes = a_deletes.strip('\n')

            a_befores = a_befores.strip(' ')
            a_befores = a_befores.strip('\n')
            a_afters = a_afters.strip(' ')
            a_afters = a_afters.strip('\n')

            #add to actual results list, starting at a_results[3]
            a_results.append(a_processed)         # [3] = processed
            a_results.append(a_notprocessed)      # [4] = not processed

            a_results.append(a_errors)            # [5] = errors
            a_results.append(a_inserts)           # [6] = inserts
            a_results.append(a_deletes)           # [7] = deletes 
            a_results.append(a_befores)           # [8] = befores
            a_results.append(a_afters)            # [9] = afters

                                        
        except ValueError as e:
            #MsgBox("process STAfile exception = %s" % e,'Exception Error')
            f1.write("process STAfile exception = %s\n" % e)
            return False
            
        #write log
        f1.write("stafile = %s\n" % a_results[0])
        f1.write("user name = %s\n" % a_results[1])
        f1.write("location  = %s\n" % a_results[2])
        f1.write("actual processed  = %s\n" % a_results[3])
        f1.write("actual not processed  = %s\n" % a_results[4])

        f1.write("actual errors  = %s\n" % a_results[5])
        f1.write("actual inserts  = %s\n" % a_results[6])
        f1.write("actual deletes  = %s\n" % a_results[7])
        f1.write("actual befores  = %s\n" % a_results[8])
        f1.write("actual afters  = %s\n\r" % a_results[9])

        return True
        
    else:
         f1.write("%s  file not exists in %s\n\r" % (a_stafile, STAfilepath))
         return False


def obtain_actual_result_from_STA_files(a_results, f1, e_results, mapdrive):
    """
    Obtain actual results from STA files
    """
    
    #read STA, ERR, AUTOCOR, PERR files from dest directory        
    stafile = e_results[0].split('.')
    a_stafile = stafile[0] + '.' + 'sta'

##    obtain the latest file having the same filename and increment extension.....example: 
##    # file prefix is the file name part of e_results[0]
##    sta_fileprefix = stafile[0]
##    fileextension = 'STA'
##    dirpath = e_results[3] + "/" + e_results[4] + "/" + e_results[2] + "/Providers/Provider" + e_results[1] + "/" + e_results[1] + "/"
##    
##    # sort dest on modified date with same file name and latest extension
##    a_stafile = get_latest_file_same_extension(dirpath, sta_fileprefix, fileextension)

##    #write log
##    f1.write("After sort dir, latest sta file selected = %s\n\r" % a_stafile)
##    f1.write("\n\r")

    
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"    
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\" 

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\" 
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    STAfilepath = dest + a_stafile
    
    # Only run when a_stafile exists
    if os.path.exists(STAfilepath) and IsValid_ALI_STA(STAfilepath, f1):
        
        #add to actual results list
        a_results.append(a_stafile)
        a_results.append(e_results[1])
        a_results.append(e_results[2])        
        
        #write log
        f1.write("Obtain actual results from %s\n\r" % STAfilepath)
        f1.write("dest = %s\n\r" % dest)
                
        try:
            
            data_file = open(STAfilepath,'r')
                        
            for line in data_file:
                if re.match("(.*)Processed:(.*)", line):
                    a_processed = line[25:len(line)]
                                    
                if re.match("(.*)Errors:(.*)", line):
                    a_errors = line[14:len(line)]

                if re.match("Data Errors(.*)", line):
                    a_data_errors = line[23:len(line)]

                if re.match("Functional Errors(.*)", line):
                    a_func_errors = line[58:len(line)]

                if re.match("Portability Errors(.*)", line):
                    a_port_errors = line[58:len(line)]

                if re.match("(.*)Privacy Errors(.*)", line):
                    a_priv_errors = line[42:len(line)]
                    
                if re.match("Inserts:(.*)", line):
                    a_inserts = line[9:len(line)]

                # obtain count of Changes record 
                if re.match("Changes:(.*)", line):
                    a_changes = line[9:len(line)]
                                        
                # obtain count of 'Deletes: ' (not 'Pilot Deletes: ')
                if re.match("Deletes:(.*)", line):
                    a_deletes = line[9:len(line)]

                # obtain count of Unlocks record 
                if re.match("Unlocks:(.*)", line):
                    a_unlocks = line[9:len(line)]

                # obtain count of Changes record 
                if re.match("Migrates:(.*)", line):
                    a_migrate = line[10:len(line)]                                    

                # obtain count of Changes record 
                if re.match("Pilot Deletes:(.*)", line):
                    a_pilotdelete = line[15:len(line)]                                    

                    
            data_file.close()
            
            # strip all the trailing spaces
            a_processed = a_processed.strip(' ')
            a_processed = a_processed.strip('\n')
            a_errors = a_errors.strip(' ')
            a_errors = a_errors.strip('\n')
            a_inserts = a_inserts.strip(' ')
            a_inserts = a_inserts.strip('\n')
            a_deletes = a_deletes.strip(' ')
            a_deletes = a_deletes.strip('\n')
            a_changes = a_changes.strip(' ')
            a_changes = a_changes.strip('\n')
            a_unlocks = a_unlocks.strip(' ')
            a_unlocks = a_unlocks.strip('\n')
            a_migrate = a_migrate.strip(' ')
            a_migrate = a_migrate.strip('\n')
            a_pilotdelete = a_pilotdelete.strip(' ')
            a_pilotdelete = a_pilotdelete.strip('\n')

            a_data_errors = a_data_errors.strip(' ')
            a_data_errors = a_data_errors.strip('\n')

            a_func_errors = a_func_errors.strip(' ')
            a_func_errors = a_func_errors.strip('\n')

            a_port_errors = a_port_errors.strip(' ')
            a_port_errors = a_port_errors.strip('\n')

            a_priv_errors = a_priv_errors.strip(' ')
            a_priv_errors = a_priv_errors.strip('\n')


            #add to actual results list
            a_results.append(a_inserts)        #a_results[3]
            a_results.append(a_processed)      #a_results[4]
            a_results.append(a_errors)         #a_results[5]
            a_results.append(a_deletes)        #a_results[6]
            a_results.append(a_changes)        #a_results[7]
            a_results.append(e_results[11])    #a_results[8]  append autocorrect from e_results[11]
            a_results.append(a_unlocks)        #a_results[9]
            a_results.append(a_migrate)        #a_results[10]
            a_results.append(a_pilotdelete)    #a_results[11]

            #add more errors
            a_results.append(a_data_errors)    #a_results[12]
            a_results.append(a_func_errors)    #a_results[13]
            a_results.append(a_port_errors)    #a_results[14]
            a_results.append(a_priv_errors)    #a_results[15] 
                                        
        except ValueError as e:
            #MsgBox("process STAfile exception = %s" % e,'Exception Error')
            f1.write("process STAfile exception = %s\n" % e)
            return False
            
        #write log
        f1.write("statfile  = %s\n" % a_results[0])
        f1.write("companyID  = %s\n" % a_results[1])
        f1.write("location  = %s\n" % a_results[2])
        f1.write("\n\r")
        f1.write("actual inserts  = %s\n" % a_results[3])
        f1.write("actual processed  = %s\n" % a_results[4])
        f1.write("actual errors   = %s\n" % a_results[5])
        f1.write("actual deletes  = %s\n" % a_results[6])
        f1.write("actual changes  = %s\n" % a_results[7])
        f1.write("actual autocorrect  = %s\n" % a_results[8])
        f1.write("actual unlock  = %s\n" % a_results[9])
        f1.write("actual migrate  = %s\n" % a_results[10])
        f1.write("actual pilot delete  = %s\n\r" % a_results[11])

        f1.write("actual data error  = %s\n" % a_results[12])
        f1.write("actual func error  = %s\n" % a_results[13])
        f1.write("actual port error  = %s\n" % a_results[14])
        f1.write("actual private error  = %s\n\r" % a_results[15])

        """
        'Changes' in sta indicates the number of records that had Function
        of Change 'C' (for change), at the beginning of the line in the dat file (instead of 'I' or 'D')
        """
        return True
        
    else:
        #write log
        f1.write("%s  file not exists in %s\n\r" % (a_stafile, STAfilepath))
        return False


def obtain_actual_result_from_MSTA_files(a_msta_results, f1, e_msta_results, e_results, mapdrive):
    """
    Obtain actual results from MSTA files. Only process when MSTA file exists (Service Orders in Reprocessing Queue)
    """
    #read MSTA file from dest directory        
    mstafile = e_results[0].split('.')
    a_mstafile = mstafile[0] + '.' + 'msta'
    
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\" 
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    
    MSTAfilepath = dest + a_mstafile
    
    # Only run when a_mstafile exists
    if (os.path.exists(MSTAfilepath) and IsValid_ALI_STA(MSTAfilepath, f1)):
                
        #add to actual results list
        a_msta_results.append(a_mstafile)
        a_msta_results.append(e_results[1])
        a_msta_results.append(e_results[2])        
        
        #write log
        f1.write("Obtain actual results from %s\n\r" % MSTAfilepath)
        f1.write("dest = %s\n\r" % dest)
                
        try:            
            data_file = open(MSTAfilepath,'r') 
                      
            for line in data_file:

                if re.match("(.*)Processed:(.*)", line):
                    a_processed = line[25:len(line)]
                                    
                if re.match("(.*)Errors:(.*)", line):
                    a_errors = line[14:len(line)]

                if re.match("Data Errors(.*)", line):
                    a_data_errors = line[23:len(line)]

                if re.match("Functional Errors(.*)", line):
                    a_func_errors = line[58:len(line)]

                if re.match("Portability Errors(.*)", line):
                    a_port_errors = line[58:len(line)]

                if re.match("(.*)Privacy Errors(.*)", line):
                    a_priv_errors = line[42:len(line)]
                    
                if re.match("Inserts:(.*)", line):
                    a_inserts = line[9:len(line)]

                # obtain count of Changes record 
                if re.match("Changes:(.*)", line):
                    a_changes = line[9:len(line)]

                # obtain count of 'Deletes: ' (not 'Pilot Deletes: ')
                if re.match("Deletes:(.*)", line):
                    a_deletes = line[9:len(line)]

                # obtain count of 'Unlocks: '
                if re.match("Unlocks:(.*)", line):
                    a_unlocks = line[9:len(line)]
                    
                # obtain count of Migrates record 
                if re.match("Migrates:(.*)", line):
                    a_migrates = line[9:len(line)]

                # obtain count of Pilot Deletes record 
                if re.match("Pilot Deletes:(.*)", line):
                    a_pdeletes = line[14:len(line)]

            data_file.close()

            # strip all the trailing spaces
            a_processed = a_processed.strip(' ')
            a_processed = a_processed.strip('\n')
            a_errors = a_errors.strip(' ')
            a_errors = a_errors.strip('\n')
            a_inserts = a_inserts.strip(' ')
            a_inserts = a_inserts.strip('\n')
            a_deletes = a_deletes.strip(' ')
            a_deletes = a_deletes.strip('\n')
            a_changes = a_changes.strip(' ')
            a_changes = a_changes.strip('\n')
            a_unlocks = a_unlocks.strip(' ')
            a_unlocks = a_unlocks.strip('\n')
            a_migrates = a_migrates.strip(' ')
            a_migrates = a_migrates.strip('\n')
            a_pdeletes = a_pdeletes.strip(' ')
            a_pdeletes = a_pdeletes.strip('\n')

            a_data_errors = a_data_errors.strip(' ')
            a_data_errors = a_data_errors.strip('\n')

            a_func_errors = a_func_errors.strip(' ')
            a_func_errors = a_func_errors.strip('\n')

            a_port_errors = a_port_errors.strip(' ')
            a_port_errors = a_port_errors.strip('\n')

            a_priv_errors = a_priv_errors.strip(' ')
            a_priv_errors = a_priv_errors.strip('\n')

            #add to actual results list
            a_msta_results.append(a_inserts)
            a_msta_results.append(a_processed)
            a_msta_results.append(a_errors)
            a_msta_results.append(a_deletes)
            a_msta_results.append(a_changes)
            a_msta_results.append(a_unlocks)
            a_msta_results.append(a_migrates)
            a_msta_results.append(a_pdeletes)

            #add more errors
            a_msta_results.append(a_data_errors)    #a_msta_results[12]
            a_msta_results.append(a_func_errors)    #a_msta_results[13]
            a_msta_results.append(a_port_errors)    #a_msta_results[14]
            a_msta_results.append(a_priv_errors)    #a_msta_results[15]       
                        
                                        
        except ValueError as e:
            #MsgBox("process MSTAfile exception = %s" % e,'Exception Error')
            f1.write("process MSTAfile exception = %s" % e)
            return False
            
        #write log
        f1.write("statfile  = %s\n" % a_msta_results[0])
        f1.write("username  = %s\n" % a_msta_results[1])
        f1.write("location   = %s\n" % a_msta_results[2])
        f1.write("actual inserts  = %s\n" % a_msta_results[3])
        f1.write("actual processed  = %s\n" % a_msta_results[4])
        f1.write("actual errors  = %s\n" % a_msta_results[5])
        f1.write("actual deletes  = %s\n" % a_msta_results[6])
        f1.write("actual changes  = %s\n" % a_msta_results[7])
        f1.write("actual unlocks  = %s\n" % a_msta_results[8])
        f1.write("actual migrates  = %s\n" % a_msta_results[9])
        f1.write("actual Pilot Deletes  = %s\n\r" % a_msta_results[10])

        f1.write("actual data error = %s\n" % a_msta_results[11])
        f1.write("actual func error = %s\n" % a_msta_results[12])
        f1.write("actual port error = %s\n" % a_msta_results[13])
        f1.write("actual private error = %s\n\r" % a_msta_results[14])

        """
        'Changes' in sta indicates the number of records that had Function
        of Change 'C' (for change), at the beginning of the line in the dat file (instead of 'I' or 'D')
        """
        return True


    else:

        f1.write("No occurence of   %s   in %s\n\r" % (a_mstafile, dest))


def msag_obtain_actual_result_from_MSTA_files(a_msta_results, f1, e_msta_results, e_results, mapdrive):
    """
    Obtain actual results from MSTA files. Only process when MSTA file exists (Service Orders in Reprocessing Queue)
    """
    #read MSTA file from dest directory        
    mstafile = e_results[1].split('.')
    a_mstafile = mstafile[0] + '.' + 'msta'
    
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    
    MSTAfilepath = dest + a_mstafile
    
    # Only run when a_mstafile exists
    if (os.path.exists(MSTAfilepath) and IsValid_MSAG_STA(MSTAfilepath, f1)):
                
        #add to actual results list
        a_msta_results.append(a_mstafile)           # statfile
        a_msta_results.append(e_results[4])         # username
        a_msta_results.append(e_results[5])         # location   
        
        #write log
        f1.write("Obtain actual results from %s\n\r" % MSTAfilepath)
        f1.write("dest = %s\n\r" % dest)
               
        try:
            
            data_file = open(MSTAfilepath,'r')            
            for line in data_file:
               
                if re.match("(.*)Processed:(.*)", line):
                    a_processed = line[25:len(line)]
                                    
                if re.match("(.*)Errors:(.*)", line):
                    a_errors = line[14:len(line)]
                    
                if re.match("Inserts:(.*)", line):
                    a_inserts = line[9:len(line)]

                # obtain count of Changes record 
                if re.match("Changes:(.*)", line):
                    a_changes = line[9:len(line)]

                # obtain count of 'Deletes: ' (not 'Pilot Deletes: ')
                if re.match("Deletes:(.*)", line):
                    a_deletes = line[9:len(line)]

                # obtain count of 'Unlocks: '
                if re.match("Unlocks:(.*)", line):
                    a_unlocks = line[9:len(line)]
                    
                # obtain count of Migrates record 
                if re.match("Migrates:(.*)", line):
                    a_migrates = line[9:len(line)]

                # obtain count of Pilot Deletes record 
                if re.match("Pilot Deletes:(.*)", line):
                    a_pdeletes = line[14:len(line)]
                    

            data_file.close()
            
            # strip all the trailing spaces
            a_processed = a_processed.strip(' ')
            a_processed = a_processed.strip('\n')
            a_errors = a_errors.strip(' ')
            a_errors = a_errors.strip('\n')
            a_inserts = a_inserts.strip(' ')
            a_inserts = a_inserts.strip('\n')
            a_deletes = a_deletes.strip(' ')
            a_deletes = a_deletes.strip('\n')
            a_changes = a_changes.strip(' ')
            a_changes = a_changes.strip('\n')
            a_unlocks = a_unlocks.strip(' ')
            a_unlocks = a_unlocks.strip('\n')
            a_migrates = a_migrates.strip(' ')
            a_migrates = a_migrates.strip('\n')
            a_pdeletes = a_pdeletes.strip(' ')
            a_pdeletes = a_pdeletes.strip('\n')

            #add to actual results list
            a_msta_results.append(a_inserts)
            a_msta_results.append(a_processed)
            a_msta_results.append(a_errors)
            a_msta_results.append(a_deletes)
            a_msta_results.append(a_changes)
            a_msta_results.append(a_unlocks)
            a_msta_results.append(a_migrates)
            a_msta_results.append(a_pdeletes)

            #a_msta_results.append(e_results[11])    # append autocorrect from e_results[11]           
                                        
        except ValueError as e:
            #MsgBox("process MSTAfile exception = %s\n" % e,'Exception Error')
            f1.write("process MSTAfile exception = %s\n" % e)
            return False
            
        #write log
        f1.write("statfile                   = %s\n" % a_msta_results[0])
        f1.write("username                   = %s\n" % a_msta_results[1])
        f1.write("location                   = %s\n" % a_msta_results[2])
        f1.write("actual inserts             = %s\n" % a_msta_results[3])
        f1.write("actual processed           = %s\n" % a_msta_results[4])
        f1.write("actual errors              = %s\n" % a_msta_results[5])
        f1.write("actual deletes             = %s\n" % a_msta_results[6])
        f1.write("actual changes             = %s\n" % a_msta_results[7])
        f1.write("actual unlocks             = %s\n" % a_msta_results[8])
        f1.write("actual migrates            = %s\n" % a_msta_results[9])
        f1.write("actual Pilot Deletes       = %s\n\r" % a_msta_results[10])

        """
        'Changes' in sta indicates the number of records that had Function
        of Change 'C' (for change), at the beginning of the line in the dat file (instead of 'I' or 'D')
        """
        return True

    else:
        f1.write("No occurence of   %s   in %s\n\r" % (a_mstafile, dest))


def obtain_error_codes_from_MERR_file(e_results, f1, merr_err_code, ecode, mapdrive):
    """
    Obtain error codes from MERR files. Only process when MSTA file exists (Service Orders in Reprocessing Queue)
    """
    merrfile = e_results[0].split('.')
    a_merrfile = merrfile[0] + '.' + 'merr'
    
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    MERRfilepath = dest + a_merrfile
        
    #write log
    f1.write("\n\r")
    f1.write("Obtain error codes from %s\n\r" % MERRfilepath)   

    try:
        if (os.path.exists(MERRfilepath) and IsValid_ALI_ERR(MERRfilepath, f1)):
        
            data_file = open(MERRfilepath,'r')           
            for line in data_file:                    
                if re.match("[0-9]* (.*)", line):
                    err = line[0:3]
                    merr_err_code.append(err)                                      
            data_file.close()

            # count occurences of each errorcode
            cnt_merrorcode = {}        #initialize dictionary
            cnt_merrorcode = count_errorcode_on_list(merr_err_code)
                
            f1.write("Count occurences of each errorcode = %s\n\r" % cnt_merrorcode)
                              
            return (True, cnt_merrorcode)
                                      
        else:
            #write log
            f1.write("No occurence of   %s  in %s\n\r" % (a_merrfile, MERRfilepath))


    except ValueError as e:
        f1.write("process MERRfile exception = %s" % e)
        return False


def msag_obtain_error_codes_from_MERR_file(e_results, f1, merr_err_code, ecode, mapdrive):
    """
    Obtain error codes from MERR files. Only process when MSTA file exists (Service Orders in Reprocessing Queue)
    """
    merrfile = e_results[1].split('.')
    a_merrfile = merrfile[0] + '.' + 'merr'
    
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    MERRfilepath = dest + a_merrfile
        
    #write log
    f1.write("Obtain error codes from %s\n" % MERRfilepath)   

    try:
        if (os.path.exists(MERRfilepath) and IsValid_MSAG_ERR(MERRfilepath, f1)):
        
            data_file = open(MERRfilepath,'r')           
            for line in data_file:                    
                if re.match("[0-9]* (.*)", line):
                    err = line[0:3]
                    merr_err_code.append(err)                                      
            data_file.close()

            # count occurences of each errorcode
            cnt_merrorcode = {}        #initialize dictionary
            cnt_merrorcode = count_errorcode_on_list(merr_err_code)
                
            f1.write("Count occurences of each errorcode = %s\n" % cnt_merrorcode)
            return (True, cnt_merrorcode)
                                      
        else:
            f1.write("No occurence of   %s   in %s\n\r" % (a_merrfile, dest))


    except ValueError as e:
        f1.write("process MERRfile exception = %s" % e)
        return False


def msag_obtain_error_codes_from_ERR_file(e_results, f1, err_code, ecode, mapdrive):
    """
    Obtain error codes from ERR files
    """
    errfile = e_results[1].split('.')
    a_errfile = errfile[0] + '.' + 'err'
    
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    ERRfilepath = dest + a_errfile
        
    #write log
    f1.write("Obtain error codes from %s\n" % ERRfilepath)

    try:
        if (os.path.exists(ERRfilepath) and IsValid_MSAG_ERR(ERRfilepath, f1)):
            
            e_notprocessed = ''
                   
            data_file = open(ERRfilepath,'r')           
            for line in data_file:                
                
                if re.match("Total Records Processed:(.*)", line):
                    e_processed = line[25:len(line)]

                # obtain count of Not Processed record 
                if re.match("Total Records Not Processed(.*)", line):
                    e_notprocessed = line[46:len(line)]
                                                        
                if re.match("Total Errors:(.*)", line):
                    e_errors = line[14:len(line)]

                                   
                if re.match("[0-9]* (.*)", line):
                    err = line[0:3]
                    err_code.append(err) 

            data_file.close()

            if (e_notprocessed == ''):
                e_notprocessed = ' 0\n'

            e_processed = e_processed.strip(' ')
            e_processed = e_processed.strip('\n')
            e_notprocessed = e_notprocessed.strip(' ')
            e_notprocessed = e_notprocessed.strip('\n')
            e_errors = e_errors.strip(' ')
            e_errors = e_errors.strip('\n')

            f1.write("Summary Report from  %s:\n\r" % a_errfile)
            f1.write("\n\r")
            f1.write("Total Records Processed     = %s\n" % e_processed)
            f1.write("Total Records Not Processed = %s\n" % e_notprocessed)
            f1.write("Total Errors                = %s\n\r" % e_errors)

            # count occurences of each errorcode
            cnt_errorcode = {}        #initialize dictionary
            cnt_errorcode = count_errorcode_on_list(err_code)
                
            f1.write("Count occurences of each errorcode = %s\n\r" % cnt_errorcode)
            return (True, cnt_errorcode)
                                      
        else:
            #MsgBox("%s  file not exists in %s\n\r" % (a_errfile, ERRfilepath),'File Not Found')
            #write log
            f1.write("%s  file not exists in %s\n\r" % (a_errfile, ERRfilepath))
            return False

    except ValueError as e:
        #MsgBox("process ERRfile exception = %s" % e,'Exception Error')
        f1.write("process ERRfile exception error = %s\n" % e)
        return False



def obtain_error_codes_from_ERR_file(e_results, f1, err_code, ecode, mapdrive):
    """
    Obtain error codes from ERR files
    """
    errfile = e_results[0].split('.')
    a_errfile = errfile[0] + '.' + 'err'
    
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    ERRfilepath = dest + a_errfile
        
    #write log
    f1.write("Obtain error codes from %s\n" % ERRfilepath)   
 
    try:
        if (os.path.exists(ERRfilepath) and IsValid_ALI_ERR(ERRfilepath, f1)):
                    
            data_file = open(ERRfilepath,'r')           
            for line in data_file:                    
                if re.match("[0-9]* (.*)", line):
                    err = line[0:3]
                    err_code.append(err)                                      
            data_file.close()

            # count occurences of each errorcode
            cnt_errorcode = {}        #initialize dictionary
            cnt_errorcode = count_errorcode_on_list(err_code)
                
            f1.write("Count occurences of each errorcode = %s\n\r" % cnt_errorcode)
            return (True, cnt_errorcode)
                                      
        else:
            #MsgBox("%s  file not exists in %s\n\r" % (a_errfile, ERRfilepath),'File Not Found')
            #write log
            f1.write("%s  file not exists in %s\n\r" % (a_errfile, ERRfilepath))
            return False

    except ValueError as e:
        f1.write("ERRfile exception error= %s\n\r" % e)
        return False


def msag_verify_error_code_in_STA_file(a_results, e_results, f1, a_err_code, ecode, mapdrive):
    """
    verify error codes in STA file
    """
    datfile = e_results[1].split('.')
    stafile = datfile[0] + '.' + 'sta'
            
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    STAfilepath = dest + stafile

    # Only when stafile exists
    if (os.path.exists(STAfilepath) and IsValid_MSAG_STA(STAfilepath, f1)):
        
        #write log
        f1.write("Verify error codes from %s\n\r" % STAfilepath)   
        
        cnt_sta_errorcode = {}      # initialize dictionary count occurences of each errorcode in STA         
        try:
            data_file = open(STAfilepath,'r')            
            for line in data_file:                
                  if re.match("(.*)\t(.*)\t errors",line):
                      s = line.split('\t')
                      if s[0] != '0':
                         #count is s[0], error code is s[1]
                         #a_err_code.append(s[0])   do not record count
                         a_err_code.append(s[1])

                         #update cnt_sta_errorcode dictionary
                         cnt_sta_errorcode.update( {s[1]:s[0]} )
                
            data_file.close()
                                           
            #write log
            f1.write("Actual error code = %s\n" % a_err_code)
            f1.write("Count occurences of each errorcode  = %s\n" % cnt_sta_errorcode)

            errdict = build_msag_ecode()
            try:
                if len(ecode) != 0:
                    e_desc = ''              
                    for err in a_err_code:
                        #e_desc = get_e_desc(err, errdict)
                        e_desc = get_msag_e_desc(err, errdict)
                    
                        if e_desc != '':
                            f1.write("Error code:  %s  =  %s\n\r" % (err, e_desc))

            except ValueError as e1:
                #MsgBox("process STAfile exception = %s\n" % e1,'Exception Error')
                f1.write("process STAfile exception = %s\n" % e1)
                return False
               
            return (True, cnt_sta_errorcode)

        except ValueError as e:
            #MsgBox("process STAfile exception = %s\n" % e,'Exception Error')
            f1.write("process STAfile exception = %s\n" % e)
            return False

    else:
        #write log
        f1.write("%s  file not exists in %s\n\r" % (stafile, dest))
        return False


def verify_error_code_in_STA_file(a_results, e_results, f1, a_err_code, ecode, mapdrive):
    """
    verify error codes in STA file
    """
    stafile = a_results[0]        
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    STAfilepath = dest + stafile

    # Only when stafile exists
    if (os.path.exists(STAfilepath) and IsValid_ALI_STA(STAfilepath, f1)):
        
        #write log
        f1.write("Verify error codes from %s\n" % STAfilepath)   
        
        cnt_sta_errorcode = {}      # initialize dictionary count occurences of each errorcode in STA         
        try:
            data_file = open(STAfilepath,'r')            
            for line in data_file:                
                  if re.match("(.*)\t(.*)\t errors",line):
                      s = line.split('\t')
                      if s[0] != '0':
                         #count is s[0], error code is s[1]
                         #a_err_code.append(s[0])   do not record count
                         a_err_code.append(s[1])

                         #update cnt_sta_errorcode dictionary
                         cnt_sta_errorcode.update( {s[1]:s[0]} )
                
            data_file.close()
                                           
            #write log
            f1.write("Actual error code = %s\n" % a_err_code)
            f1.write("Count occurences of each errorcode  = %s\n\r" % cnt_sta_errorcode)

            errdict = build_ecode()
            try:
                if len(ecode) != 0:
                    e_desc = ''              
                    for err in a_err_code:
                        e_desc = get_e_desc(err, errdict)
                    
                        if e_desc != '':
                            f1.write("Error code:  %s  =  %s\n\r" % (err, e_desc))

            except ValueError as e1:
                f1.write("process STAfile exception = %s" % e1)
                return False
               
            return (True, cnt_sta_errorcode)

        except ValueError as e:
            f1.write("process STAfile exception = %s\n" % e)
            return False

    else:
        #write log
        f1.write("%s  file not exists in %s\n\r" % (stafile, dest))
        return False



def verify_error_code_in_MSTA_file(a_msta_results, a_msta_err_code, e_results, f1, ecode, mapdrive):
    """
    verify error codes in MSTA file. Only process when MSTA file exists (Service Orders in Reprocessing Queue)
    """
    mstafile = a_msta_results[0]        
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    MSTAfilepath = dest + mstafile

    # Only when stafile exists
    if (os.path.exists(MSTAfilepath) and IsValid_ALI_STA(MSTAfilepath, f1)):
        
        #write log
        f1.write("Verify error codes from %s\n" % MSTAfilepath)   
        
        cnt_msta_errorcode = {}      # initialize dictionary count occurences of each errorcode in MSTA         
        try:
            data_file = open(MSTAfilepath,'r')            
            for line in data_file:                
                  if re.match("(.*)\t(.*)\t errors",line):
                      s = line.split('\t')
                      if s[0] != '0':
                         #count is s[0], error code is s[1]
                         #a_err_code.append(s[0])   do not record count
                         a_msta_err_code.append(s[1])

                         #update cnt_sta_errorcode dictionary
                         cnt_msta_errorcode.update( {s[1]:s[0]} )
                
            data_file.close()
                                           
            #write log
            f1.write("Actual error code = %s\n" % a_msta_err_code)
            f1.write("Count occurences of each errorcode  = %s\n\r" % cnt_msta_errorcode)

            errdict = build_ecode()
            try:
                if len(ecode) != 0:
                    e_desc = ''              
                    for err in a_msta_err_code:
                        e_desc = get_e_desc(err, errdict)
                    
                        if e_desc != '':
                            f1.write("Error code:  %s  =  %s\n\r" % (err, e_desc))

            except ValueError as e1:
                #MsgBox("process MSTA file exception = %s\n" % e1,'Exception Error')
                f1.write("process MSTA file exception = %s\n" % e1)
                return False
               
            return (True, cnt_msta_errorcode)

        except ValueError as e:
            #MsgBox("process MSTA file exception = %s" % e,'Exception Error')
            f1.write("process MSTA file exception = %s" % e)
            return False

    else:
        #write log
        f1.write("%s  file not exists in %s\n\r" % (mstafile, dest))
        return False


def msag_verify_error_code_in_MSTA_file(a_msta_results, a_msta_err_code, e_results, f1, ecode, mapdrive):
    """
    verify error codes in MSTA file. Only process when MSTA file exists (Service Orders in Reprocessing Queue)
    """
    mstafile = a_msta_results[0]        
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    MSTAfilepath = dest + mstafile

    # Only when stafile exists
    if (os.path.exists(MSTAfilepath) and IsValid_MSAG_STA(MSTAfilepath, f1)):
        
        #write log
        f1.write("Verify error codes from %s\n" % MSTAfilepath)   
        
        cnt_msta_errorcode = {}      # initialize dictionary count occurences of each errorcode in MSTA         
        try:
            data_file = open(MSTAfilepath,'r')            
            for line in data_file:                
                  if re.match("(.*)\t(.*)\t errors",line):
                      s = line.split('\t')
                      if s[0] != '0':
                         #count is s[0], error code is s[1]
                         #a_err_code.append(s[0])   do not record count
                         a_msta_err_code.append(s[1])

                         #update cnt_sta_errorcode dictionary
                         cnt_msta_errorcode.update( {s[1]:s[0]} )
                
            data_file.close()
                                           
            #write log
            f1.write("Actual error code = %s\n" % a_msta_err_code)
            f1.write("Count occurences of each errorcode  = %s\n\r" % cnt_msta_errorcode)

            errdict = build_ecode()
            try:
                if len(ecode) != 0:
                    e_desc = ''              
                    for err in a_msta_err_code:
                        e_desc = get_e_desc(err, errdict)
                    
                        if e_desc != '':
                            f1.write("Error code:  %s  =  %s\n\r" % (err, e_desc))

            except ValueError as e1:
                #MsgBox("process MSTA file exception = %s\n" % e1,'Exception Error')
                f1.write("process MSTA file exception = %s\n" % e1)
                return False
               
            return (True, cnt_msta_errorcode)

        except ValueError as e:
            f1.write("process MSTA file exception = %s\n" % e1)
            return False

    else:
        #write log
        f1.write("%s  file not exists in %s\n" % (mstafile, dest))
        return False


def msag_obtain_processing_error(e_results, f1, cfg_file, mapdrive):
    """
    Verify in PERR file for descriptive processing error
    """
    perrfile = e_results[1].split('.')
    a_perrfile = perrfile[0] + '.' + 'perr'
    perror_description = ''
    
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    PERRfilepath = dest + a_perrfile
    
    try:
        # Only run when a_perrfile exists
        if  os.path.exists(PERRfilepath):
            data_file = open(PERRfilepath,'r')
            pat1 = 'An error has occurred in the Service Order Processing.'
            pat2 = 'Error Processing File:(.*)'
            pat3 = 'The following service orders were not processed:'
            perr_description = ''
            d_perr_description = ''
            err_description = ''
            not_processed = ''
            a1 = re.compile(pat1)
            a2 = re.compile(pat2)
            a3 = re.compile(pat3)

            for line in data_file:

                if re.match(a1, line):
                    tmp = len(line)
                    d_perr_description = line[63:tmp]

                if re.match(a2, line):
                    tmp = len(line)
                    perr_description = line[23:tmp]

                # get error description
                if re.match("[A-Za-z ']*. (.*)", line):
                    err_description = line               
                
                # get not processed
                if re.match(a3, line):
                    not_processed = 'continue'
                    break
                                 
            data_file.close()
            return (perr_description, d_perr_description, err_description, not_processed)
            
        else:
            #write log
            f1.write("%s  file not exists in %s\n" % (perrfile, dest))               
        
    except:
        #write log
        f1.write("Exception in PERR file\n")


def msag_obtain_autocorrection(e_results, f1, mapdrive):
    """
    Verify in AUTOCOR file for count of records Auto-Corrected
    """
    autocorrfile = e_results[1].split('.')
    a_autocorrfile = autocorrfile[0] + '.' + 'autocor'

    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    AUTOCORfilepath = dest + a_autocorrfile

    count_of_autocorrect = 0
    autocorrect_err_code = []

    try:
        # Only run when AUTOCOR file exists
        if  os.path.exists(AUTOCORfilepath) and IsValid_AUTOCORR():
            data_file = open(AUTOCORfilepath,'r')
            pat = 'Total Records Auto-Corrected: *'           
            for line in data_file:
                a1 = re.compile(pat)
                if re.match(pat, line):
                    tmp = len(line)
                    autocorr = line[30:tmp]                        
                    #return autocorr                   
                    count_of_autocorrect = autocorr

                # get all errorcodes
                if re.match("[0-9]* (.*)", line):
                    err = line[0:3]
                    autocorrect_err_code.append(err)

            data_file.close()

            ## do this to get all errorcodes
            #autocorrect_err_code = []
            #data_file = open(AUTOCORfilepath,'r')           
            #for line in data_file:                    
            #    if re.match("[0-9]* (.*)", line):
            #        err = line[0:3]
            #        autocorrect_err_code.append(err)                                      
            #data_file.close()

            # count occurences of each errorcode
            cnt_errorcode = {}        #initialize dictionary
            cnt_errorcode = count_errorcode_on_list(autocorrect_err_code)
            
            #write log
            f1.write("Verify error codes from %s\n" % AUTOCORfilepath)   
            f1.write("Actual autocorrect count %s\n" % count_of_autocorrect)   
            f1.write("count occurences of every autocorrect errorcodes %s\n" % cnt_errorcode)   

            return count_of_autocorrect
                           
        else:
            #write log
            f1.write("%s  file not exists in %s\n" % (a_autocorrfile, dest))
            return 0        
    except:
        #write log
        f1.write("Exception in AUTOCOR file  %s\n" % a_autocorrfile) 
        return 0

def obtain_processing_error(e_results, f1, cfg_file, mapdrive):
    """
    Verify in PERR file for descriptive processing error
    """
    perrfile = e_results[0].split('.')
    a_perrfile = perrfile[0] + '.' + 'perr'
    perror_description = ''
    
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    PERRfilepath = dest + a_perrfile

    try:
        # Only run when a_perrfile exists
        if  os.path.exists(PERRfilepath):
            data_file = open(PERRfilepath,'r')
            pat1 = 'An error has occurred in the Service Order Processing.'
            pat2 = 'Error Processing File:(.*)'
            pat3 = 'The following service orders were not processed:'
            perr_description = ''
            d_perr_description = ''
            err_description = ''
            not_processed = ''
            a1 = re.compile(pat1)
            a2 = re.compile(pat2)
            a3 = re.compile(pat3)
                 
            for line in data_file:
                
                if re.match(a1, line):
                    tmp = len(line)
                    d_perr_description = line[63:tmp]
                
                if re.match(a2, line):
                    tmp = len(line)
                    perr_description = line[23:tmp]

                # get error description
                if re.match("[A-Za-z ']*. (.*)", line):
                    err_description = line               
                
                # get not processed               
                if re.match(a3, line):
                    not_processed = 'continue'
                    break
                                     
            data_file.close()
            return (perr_description, d_perr_description, err_description, not_processed)
            
        else:
            #write log
            f1.write("%s  file not exists in %s\n" % (a_perrfile, dest))               
        
    except:
        #write log
        f1.write("Exception in PERR file\n")

def obtain_autocorrection(e_results, f1, mapdrive):
    """
    Verify in AUTOCOR file for count of records Auto-Corrected
    """
    autocorrfile = e_results[0].split('.')
    a_autocorrfile = autocorrfile[0] + '.' + 'autocor'

    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    AUTOCORfilepath = dest + a_autocorrfile

    count_of_autocorrect = 0
    autocorrect_err_code = []

    try:
        # Only run when AUTOCOR file exists
        if  os.path.exists(AUTOCORfilepath) and IsValid_ALI_AUTOCORRECTION(AUTOCORfilepath, f1):
            data_file = open(AUTOCORfilepath,'r')
            pat = 'Total Records Auto-Corrected: *'           
            for line in data_file:
                a1 = re.compile(pat)
                if re.match(pat, line):
                    tmp = len(line)
                    autocorr = line[30:tmp]                        
                    #return autocorr                   
                    count_of_autocorrect = autocorr

                # get all errorcodes
                if re.match("[0-9]* (.*)", line):
                    err = line[0:3]
                    autocorrect_err_code.append(err)

            data_file.close()

            ## do this to get all errorcodes
            #autocorrect_err_code = []
            #data_file = open(AUTOCORfilepath,'r')           
            #for line in data_file:                    
            #    if re.match("[0-9]* (.*)", line):
            #        err = line[0:3]
            #        autocorrect_err_code.append(err)                                      
            #data_file.close()

            # count occurences of each errorcode
            cnt_errorcode = {}        #initialize dictionary
            cnt_errorcode = count_errorcode_on_list(autocorrect_err_code)
            
            #write log
            f1.write("Verify error codes from %s\n" % AUTOCORfilepath)   
            f1.write("Actual autocorrect count %s\n" % count_of_autocorrect)
            f1.write("count occurences of every autocorrect errorcodes %s\n\r" % cnt_errorcode)   

            return cnt_errorcode, count_of_autocorrect
                           
        else:
            #write log
            f1.write("%s  file not exists in %s\n" % (a_autocorrfile, dest))
            return 0        
    except:
        #write log
        f1.write("Exception in AUTOCOR file  %s\n" % a_autocorrfile) 
        return 0


def queue_error_QERR_process(e_results, f1, mapdrive):

    #Verify if there is QERR file exists, then obtain the processing error from QERR file, then no more testing.
    qerrfile = e_results[0].split('.')
    a_qerrfile = qerrfile[0] + '.' + 'qerr'
    qerror_description = ''
                
    # verify PERR file processing
    #dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    #dest = "Z:\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"
    else: 
            dest = e_results[3] + "\\" + e_results[4] + "\\" + e_results[2] + "\\Providers\\Provider" + e_results[1] + "\\" + e_results[1] + "\\"

    QERRfilepath = dest + a_qerrfile

    try:          
        # Only run when a_qerrfile exists
        if  os.path.exists(QERRfilepath):
            data_file = open(QERRfilepath,'r')
            pat = 'An error has occurred in the Service Order Queuing process.'            
            for line in data_file:

                if re.match("COMPANY ID :(.*)", line):
                    companyID = line[12:len(line)]

                if re.match("Error Time:(.*)", line):
                    ErrorTime = line[11:len(line)]

                a1 = re.compile(pat)
                if re.match(a1, line):
                    tmp = len(line)
                    qerror_description = line[59:tmp]       # was 59 ?? should it be 63 ?

                if re.match("(.*).dat", line):
                    error_dat_file = line
                    break
                                  
            data_file.close()

            companyID = companyID.strip(' ')
            companyID = companyID.strip('\n')
            ErrorTime = ErrorTime.strip('\n')
            error_dat_file = error_dat_file.strip('\n')

            if len(qerror_description) > 0:
                #write log
                f1.write("ALI SOI QUEUE ERROR\n")
                f1.write("COMPANY ID : %s\n" % companyID)
                f1.write("Error Time : %s\n\r" % ErrorTime)
                f1.write("Queue Processing Error from  %s:\n\r %s\n" % (a_qerrfile, qerror_description))
                f1.write("The following file cannot be processed:\n%s\n\r" % error_dat_file)
                return True
        else:
            f1.write("No occurence of   %s   in %s\n\r" % (a_qerrfile, dest))
                      
    except:
        #write log
        f1.write("%s file not exists in %s\n" % (a_qerrfile, dest))

def msag_queue_error_QERR_process(e_results, f1, mapdrive):

    #Verify if there is QERR file exists, then obtain the processing error from QERR file, then no more testing.
    qerrfile = e_results[1].split('.')
    a_qerrfile = qerrfile[0] + '.' + 'qerr'
    qerror_description = ''
                
    # verify QERR file processing
    #dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    #dest = "Z:\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    if os.path.exists(mapdrive + "\\"):
            dest = mapdrive + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"
    else: 
            dest = e_results[2] + "\\" + e_results[3] + "\\" + e_results[5] + "\\Providers\\MSAGSO\\" + e_results[4] + "\\"

    QERRfilepath = dest + a_qerrfile

    try:          
        # Only run when a_qerrfile exists
        if  os.path.exists(QERRfilepath):
            data_file = open(QERRfilepath,'r')
            pat = 'An error has occurred in the Service Order Queuing process.'            
            for line in data_file:

                if re.match("COMPANY ID :(.*)", line):
                    companyID = line[12:len(line)]

                if re.match("Error Time:(.*)", line):
                    ErrorTime = line[11:len(line)]

                a1 = re.compile(pat)
                if re.match(pat, line):
                    tmp = len(line)
                    qerror_description = line[59:tmp]    # was 59 !!!! should it be 63 ?

                if re.match("(.*).dat", line):
                    error_dat_file = line
                    break
                                  
            data_file.close()

            companyID = companyID.strip(' ')
            companyID = companyID.strip('\n')
            ErrorTime = ErrorTime.strip('\n')
            error_dat_file = error_dat_file.strip('\n')

            if len(qerror_description) > 0:
                #write log
                f1.write("ALI SOI QUEUE ERROR\n")
                f1.write("COMPANY ID : %s\n" % companyID)
                f1.write("Error Time : %s\n\r" % ErrorTime)
                f1.write("Queue Processing Error from  %s:\n\r %s\n" % (a_qerrfile, qerror_description))
                f1.write("The following file cannot be processed:\n%s\n\r" % error_dat_file)
                return True
        else:
            f1.write("No occurence of  %s  in %s\n\r" % (a_qerrfile, dest))
                                  
    except:
        #write log
        f1.write("%s file not exists in %s\n" % (a_qerrfile, dest))


def IsValid_MSAG_STA(MSAG_STAFilePath, f1):
    # Verify valid MSAG STA file - with header "MSAG PROCESSING RESULTS:"
    if  os.path.exists(MSAG_STAFilePath):
        validMSAGSTA = False
        data_file = open(MSAG_STAFilePath,'r')
        for line in data_file:
            if re.match("MSAG PROCESSING RESULTS:", line):
                validMSAGSTA = True
                break
                                  
        data_file.close()

    # write to log file
    if (validMSAGSTA):
        f1.write("%s is valid MSAG file to process.\n" % (MSAG_STAFilePath))
    else:
        f1.write("%s is NOT a valid MSAG file to process.\n" % (MSAG_STAFilePath))
    return validMSAGSTA


def IsValid_MSAG_ERR(MSAG_ERRFilePath, f1):
    # Verify valid MSAG ERR file - with header "MSAG PROCESSING ERRORS:"
    validMSAGERR = False
    if  os.path.exists(MSAG_ERRFilePath):

        data_file = open(MSAG_ERRFilePath,'r')
        for line in data_file:
            if re.match("MSAG PROCESSING ERRORS:", line):
                validMSAGERR = True
                break
                                  
        data_file.close()

    # write to log file
    if (validMSAGERR):
        f1.write("%s is valid MSAG file to process.\n" % (MSAG_ERRFilePath))
    else:
        f1.write("%s is NOT a valid MSAG file to process.\n" % (MSAG_ERRFilePath))
    return validMSAGERR


def IsValid_ALI_STA(ALI_STAFilePath, f1):
    # Verify valid ALI STA file - with header "CLEC PROCESSING RESULTS:"
    validALISTA = False
    if  os.path.exists(ALI_STAFilePath):

        data_file = open(ALI_STAFilePath,'r')
        for line in data_file:
            if re.match("CLEC PROCESSING RESULTS:", line):
                validALISTA = True
                break
                                  
        data_file.close()

    # write to log file
    if (validALISTA):
        f1.write("%s is valid ALI file to process.\n" % (ALI_STAFilePath))
    else:
        f1.write("%s is NOT a valid ALI file to process.\n" % (ALI_STAFilePath))

    return validALISTA


def IsValid_ALI_ERR(ALI_ERRFilePath, f1):
    # Verify valid ALI ERR file - with header "CLEC PROCESSING ERRORS:"
    validALIERR = False
    if  os.path.exists(ALI_ERRFilePath):

        data_file = open(ALI_ERRFilePath,'r')
        for line in data_file:
            if re.match("CLEC PROCESSING ERRORS:", line):
                validALIERR = True
                break
                                  
        data_file.close()

    # write to log file
    if (validALIERR):
        f1.write("%s is valid ALI file to process.\n" % (ALI_ERRFilePath))
    else:
        f1.write("%s is NOT a valid ALI file to process.\n" % (ALI_ERRFilePath))

    return validALIERR


def IsValid_ALI_QERR(ALI_QERRFilePath, f1):
    # Verify valid ALI QERR file - with header "ALI SOI QUEUE ERROR"
    validALIQERR = False
    if  os.path.exists(ALI_QERRFilePath):

        data_file = open(ALI_QERRFilePath,'r')
        for line in data_file:
            if re.match("ALI SOI QUEUE ERROR", line):
                validALIQERR = True
                break
                                  
        data_file.close()

    # write to log file
    if (validALIQERR):
        f1.write("%s is valid ALI file to process.\n" % (ALI_QERRFilePath))
    else:
        f1.write("%s is NOT a valid ALI file to process.\n" % (ALI_QERRFilePath))

    return validALIQERR


def IsValid_ALI_AUTOCORRECTION(ALI_AUTOCORRFilePath, f1):
    # Verify valid ALI AUTOCORR file - with header "CLEC AUTO-CORRECTION LOG"
    validALIAUTOCORR = False
    if  os.path.exists(ALI_AUTOCORRFilePath):

        data_file = open(ALI_AUTOCORRFilePath,'r')
        for line in data_file:
            if re.match("CLEC AUTO-CORRECTION LOG", line):
                validALIAUTOCORR = True
                break
                                  
        data_file.close()

    # write to log file
    if (validALIAUTOCORR):
        f1.write("%s is valid ALI file to process.\n" % (ALI_AUTOCORRFilePath))
    else:
        f1.write("%s is NOT a valid ALI file to process.\n" % (ALI_AUTOCORRFilePath))

    return validALIAUTOCORR


def Log_Starting_Process(Process, f1):
    f1.write("\n\r")
    f1.write("%s\n\r" % (Process))


def verify_error_code_in_cfg_with_actual_result(c_err_code, cnt_err_errorcode, cnt_sta_errorcode, f1):
    f1.write("c_err_code  = %s\n" % c_err_code)
    f1.write("cnt_err_errorcode = %s\n" % cnt_err_errorcode)
    f1.write("cnt_sta_errorcode  = %s\n\r" % cnt_sta_errorcode)

    result1 = False
    result2 = False

    diff1 = dict_diff(c_err_code, cnt_sta_errorcode)
    if (len(diff1) == 0):
        result1 = True

    diff2 = dict_diff(cnt_err_errorcode, cnt_sta_errorcode)
    if (len(diff2) == 0):
        result2 = True
    
    return (result1, result2)


def verify_error_code_in_cfg_with_autocor_file(c_autocorr_err_code, autocor_err_code, f1):
    f1.write("c_autocorr_err_code  = %s\n" % c_autocorr_err_code)
    f1.write("autocor_err_code = %s\n" % autocor_err_code)

    result1 = False

    diff1 = dict_diff(c_autocorr_err_code, autocor_err_code)
    if (len(diff1) == 0):
        result1 = True
    
    return result1


# compare between dictionaries, return len(dictionary) == 0 if they are equal
def dict_diff(dict_a, dict_b):
    return dict([
        (key, dict_b.get(key, dict_a.get(key)))
        for key in set(dict_a.keys()+dict_b.keys())
        if (
            (key in dict_a and (not key in dict_b or dict_a[key] != dict_b[key])) or
            (key in dict_b and (not key in dict_a or dict_a[key] != dict_b[key]))
        )
    ])



# verify msag expected results with actual results - only occurences of DONE and STA
def msag_verify_expected_with_actual_results(e_results, a_results, f1):
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
        pass3 = True
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

    allpass = pass1 and pass2 and pass3 and pass4 and pass5 and pass6 and pass7

    # write log
    f1.write("\n\r")                        
    f1.write("allpass = %s    (pass1 = %s,  pass2 = %s,  pass3 = %s,  pass4 = %s,  pass5 = %s, pass6 = %s, pass7 = %s)\n\r" % (allpass,pass1,pass2,pass3,pass4,pass5,pass6,pass7))                                                                                                         
    return allpass


# verify expected results with actual results - only occurences of DONE and STA
def verify_expected_with_actual_results(e_results, a_results, f1):

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

            #i = 0
            #for ecode in a_err_code:
            #    if a_err_code[i] in err_code:
            #        pass3 = True
            #    else:
            #        pass3 = False
            #    i = i + 1

        pass3 = True
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

    f1.write(ReportLine("Expected inserts", e_results[6], "Actual inserts", a_results[3], "pass1", pass1))
    f1.write(ReportLine("Expected processed", e_results[7], "Actual processed", a_results[4], "pass2", pass2))
    f1.write(ReportLine("Expected errors", e_results[8], "Actual errors", a_results[5], "pass3", pass3))
    f1.write(ReportLine("Expected deletes", e_results[9], "Actual deletes", a_results[6], "pass4", pass4))
    f1.write(ReportLine("Expected changes", e_results[10], "Actual changes", a_results[7], "pass5", pass5))
    f1.write(ReportLine("Expected unlock", e_results[14], "Actual unlock", a_results[9], "pass6", pass6))
    f1.write(ReportLine("Expected pilot delete", e_results[15], "Actual pilot delete", a_results[11], "pass7", pass7))
                            
    allpass = pass1 and pass2 and pass3 and pass4 and pass5 and pass6 and pass7

    # write log
    f1.write("\n\r")                        
    f1.write("allpass = %s    (pass1 = %s,  pass2 = %s,  pass3 = %s,  pass4 = %s,  pass5 = %s, pass6 = %s, pass7 = %s)\n\r" % (allpass,pass1,pass2,pass3,pass4,pass5,pass6,pass7))

    return allpass



#####################################################################################
#init wx app to use wxpython
app = wx.App(redirect=True)    # Error messages go to popup window
app.MainLoop() 
#####################################################################################