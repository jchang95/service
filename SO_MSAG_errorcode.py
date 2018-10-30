#!/usr/bin/python
# -*- coding: utf-8 -*-

# SO MSAG_error code listing = list current Service Order Error Codes
#                       with description and long description
#
# Usage: SO_MSAG_errorcode
#
  
import wx
import wx.lib.mixins.listctrl as listmix        #for listctrl column click to sort column


errdata = {
0  : ("000","No Errors"),
1  : ("205","Invalid PSAP"), 
2  : ("400","MSAG does not exist for change"),
3  : ("401","MSAG does not exist for delete"),
4  : ("402","MSAG already exists"),
5  : ("403","Change would cause overlap"),
6  : ("404","Insert would cause overlap"),
7  : ("405","ESNs, Street, or Community do not match on join"),
8  : ("406","Split would strand ANIs"),
9  : ("407","Change would strand ANIs"),
10  : ("408","Delete attempted on MSAG with ANIs attached"),
11  : ("409","High Range is less than Low Range"),
12  : ("410","High or Low Range does not match Parity"),
13  : ("411","Parity Split would strand ANIs"),
14  : ("412","Community does not exist"),
15  : ("413","ESN does not exist"),
16  : ("414","Invalid Directional"),
17  : ("415","Invalid Suffix"),
18  : ("416","Split Failed"),
19  : ("417","Invalid Parity Code"),
20  : ("418","Invalid Function Code"),
21  : ("419","Function Code Not Supported By Service Order Processing"),
22  : ("420","Street name not valid"),
23  : ("421","Street Suffix Not Valid"),
24  : ("422","Community Name Not Valid"),
25  : ("423","Join Failed"),
26  : ("450","Batch processes resulted in stranded ANIs"),
27  : ("451","Batch processes resulted in Overlap"),
}
        
class SO_Form(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, u'MSAG SO Error Codes and descriptions')
        
        # Add a panel so it looks the correct on all platforms
        panel = SO_ListCtrlPanel(self)

        # add status bar
        status = self.CreateStatusBar()

        
class SO_ListCtrl(wx.ListCtrl):
    
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        

class SO_ListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
 
        self.index = 0 
        self.list_ctrl = SO_ListCtrl(self, size=(460, 515),
                         style=wx.LC_REPORT
                         |wx.BORDER_SUNKEN
                         |wx.LC_SORT_ASCENDING
                         )
        self.SetClientSize(wx.Size(660, 455))
        
        #self.list_ctrl.SetBackgroundColour(wx.Colour(255, 255, 128))     #yellow
        self.list_ctrl.SetBackgroundColour((255,228,196))  # bisque
        
        self.list_ctrl.InsertColumn(0, "MSAG Error Code")
        self.list_ctrl.InsertColumn(1, "Description", wx.LIST_FORMAT_LEFT)

        self.list_ctrl.SetColumnWidth(0, 120)
        self.list_ctrl.SetColumnWidth(1, 320)

        items = errdata.items()
        index = 0
        
        self.RowDict = {}     # dictionary for row data
        
        for key, data in items:
            self.list_ctrl.InsertStringItem(index, str(data[0]).strip())
            
            self.list_ctrl.SetStringItem(index, 1, data[1].strip())
            
            self.list_ctrl.SetItemData(index, key)
            
            self.RowDict[index] = data
            index += 1

        #print self.RowDict
 
        # Now that the list exists we can init the other base class,
        # see wx/lib/mixins/listctrl.py
        self.itemDataMap = errdata
        
        listmix.ColumnSorterMixin.__init__(self, 2)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.list_ctrl)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list_ctrl)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 0, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(sizer)
 
    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.list_ctrl
 
    def OnColClick(self, event):
        #print "column clicked"
        event.Skip()
        
    def OnItemSelected(self, event):
        '''
        click list item and display the selected string in frame's title
        '''
        currentItem = event.m_itemIndex
        selItem = self.RowDict[self.list_ctrl.GetItemData(currentItem)]
        
##        print selItem[0]        # error code
##        print selItem[1]        # description
        
        #wx.MessageBox(selItem[2], "Long description of  error code  %s\n\r" % selItem[0], wx.STAY_ON_TOP)


if __name__ == '__main__':
    app = wx.App(False)
    frame = SO_Form()           #using SO_Form    
    frame.Show()
    app.MainLoop()
