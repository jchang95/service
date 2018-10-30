#!/usr/bin/python
# -*- coding: utf-8 -*-

# SO error code listing = list current Service Order Error Codes
#                       with description and long description
#
# Usage: SO_errorcode
#
  
import wx
import wx.lib.mixins.listctrl as listmix        #for listctrl column click to sort column

errdata = {
0  : ("000","No Errors","No Errors"),
1  : ("002","Non-numeric character in the telephone number.","Non-numeric character in the telephone number. This includes any spaces or alpha characters in the NPA  NXX  or TN fields of the telephone number. This is considered a data error."),
2  : ("003","Non-numeric character in the main telephone number.","Non-numeric character in the main telephone number. This includes any space or alpha characters in the NPA  NXX  orTN fields of the main number. This is considered a data error."),
3  : ("009","Illegal Class of Service","Illegal class of service. The class of service must be a digit from 0 to 9."),
4  : ("010","Illegal Type of Service","Illegal type of service. The type of service must be a single digit from 0 to 5."),
5  : ("103","MSAG Not Valid","MSAG Not Valid"),
6  : ("104","House Number Not Valid","House Number Not Valid"),
7  : ("105","Directional  Not Valid","Directional  Not Valid"),
8  : ("106","Street Name  Not Valid","Street Name  Not Valid"),
9  : ("107","Community Name Not Valid","Community Name Not Valid"),
10  : ("108","Exchange Matching Failed","Exchange Matching Failed"),
11  : ("109","Company ID Not Valid","Company ID Not Valid"),
12  : (110,"House Number Suffix Not Valid","House Number Suffix Not Valid"),
13  : (112,"Customer Code Not Valid","Customer Code Not Valid"),
14  : (113,"NPA_NNX Not Valid","NPA_NNX Not Valid"),
15  : (117,"Low house number is greater than the high house number.","Low house number is greater than the high house number."),
16  : (118,"Community name field not populated.","Community name field not populated. During bulk loads  the community name must be specified on every MSAG record."),
17  : (119,"Non-numeric character in ESN or blank ESN.","Non-numeric character in ESN or blank ESN. The ESN must be all numeric and must have a value greater than zero."),
18  : (120,"Community Not Found UsingExchangeField","Community Name Not Populated And Not Found Using Exchange Field"),
19  : (121,"Function of Change Code not supported by Service Order Processing","The Function of Change (FOC) code is not supported by the Admin ALI. The only supported FOCs are C, D, I, M, P, and U."),
20  : (202,"Record Does Not Exist For A Delete","Record Does Not Exist for a Delete. A service order with FOC=D was submitted for a record that does not exist."),
21  : (203,"Customer Code Does Not Match","Customer Code Does Not Match. The Customer Code in the service order does not match the Customer Code in the existing TN record."),
22  : (247,"Record Already Exists Under Different Company ID","Record Already Exists Under Different Company ID. Insert not allowed."),
23  : (255,"Max Reprocessing attempted on Migrates for Non-Existent TN","Max Reprocessing attempted on Migrates for Non-Existent TN. Hard error Associated with Error Code 205."),
24  : (301,"Migrate Failed After Max Reprocessing Attempts","Migrate Failed After Max Reprocessing Attempts, because the record remained locked."),
25  : (307,"Company IDs Do Not Match On Error Delete","Company IDs Do Not Match On Error Delete"),
26  : (309,"Record Exists With Company ID Mismatch","Record Exists With Company ID Mismatch"),
27  : (310,"Unlock Failed -  Main Account Has Sublines","Unlock Failed -  Main Account Has Sublines"),
28  : (311,"Lock Exceeds Number Of Retries","Lock Exceeds Number Of Retries"),
29  : (312,"MSAG Update Cause Of TN Error","MSAG Update Cause Of TN Error"),
30  : (314,"TN And Main Account Mismatch","TN And Main Account Mismatch"),
31  : (315,"Change Failed - Completion Date Conflict With Disconnect File","Change Failed - Completion Date Conflict With Disconnect File"),
32  : (316,"Record In Disconnect With Greater Complete Date","Record In Disconnect With Greater Complete Date"),
33  : (317,"Delete Failed - Record In TN Database Has Same Completion Date","Delete Failed - Record In TN Database Has Same Completion Date"),
34  : (321,"Pilot delete (FOC=P) was attempted on a subsidiary line.","A pilot delete (FOC=P) was attempted on a subsidiary line. A pilot delete cannot be performed on a subsidiary line. To delete a main TN and its subsidiaries, submit an FOC=P for the main number. To delete a subsidiary line only, submit an FOC=D for the subsidiary line."),
35  : (322,"Function of change (F)inal would result in a pilot delete.","Function of change (F)inal would result in a pilot delete. A (F)inal transaction was attempted that would result in the delete of an entire pilot-subsidiary group. This action must be accomplished with a (P)ilot Delete record."),
36  : (323,"FOC other than (I)nsert attempted during an initial load.","Function of change other than (I)nsert attempted during an initial load. During an initial load  no function of change other than (I)nsert is allowed. This error can also occur if a function of change of P is passed in a service order record on a system where the Pilot Processing Disable feature key is enabled."),
37  : (601,"Address not in GIS sites","Address not in GIS sites. Validation against x9GIS data fails."),
38  : (602,"Address not in GIS road ranges","Address not in GIS road ranges. Validation against x9GIS data fails."),
39  : (603,"Address not in GIS sites and/or road ranges","Address not in GIS sites and/or road ranges. Validation against x9GIS data fails."),
40  : (651,"Address not in GIS sites after reprocessing","Address not in GIS sites after reprocessing. Validation against x9GIS data fails."),
41  : (652,"Address not in GIS road ranges after reprocessing","Address not in GIS road ranges after reprocessing. Validation against x9GIS data fails."),
42  : (653,"Address not in GIS sites and/or road ranges after reprocessing","Address not in GIS sites and/or road ranges after reprocessing. Validation against x9GIS data fails."),
43  : (700,"Illegal Function Code","Illegal function of change. During a MSAG bulk load  the only valid function of change is (I)nsert."),
44  : (701,"No MSAG record found.","No MSAG record found. No MSAG record was found for this address. This includes cases where the street name does not exist in the MSAG and where the street exists but the ranges do not cover the current address."),
45  : (702,"Record Already Exists","Record Already Exists"),
46  : (705,"Record does not exist on a pilot delete.","Record does not exist on a pilot delete. An attempt was made to perform a pilot delete on a main telephone number that does not exist in the database."),
47  : (710,"Customer codes do not match on a change.","Customer codes do not match on a change. The customer code on a change to a telephone number record does not match the customer code of the existing record."),
48  : (711,"Customer codes do not match on a delete.","Customer codes do not match on a delete. The customer code on a delete or pilot delete operation does not match the customer code of the record to be deleted."),
49  : (712,"Change attempted for record that does not exist.","Change attempted for record that does not exist. An attempt was made to change a telephone number record that does not exist in the database."),
50  : (739,"Street names do not match on a delete.","Street names do not match on a delete. The street name in a service order with FOC=D does not match the street name in the database. Street name is not a required field when FOC=D, but if the field does have a value, it must match the street name value in the database."),
51  : (740,"Delete attempted on a TN with subsidiaries.","Delete attempted on a TN with subsidiaries. A delete (FOC=D) was attempted on a TN that has subsidiaries. To delete a main TN and all of its subsidiaries, submit a pilot delete (FOC=P) service order, or delete each subsidiary individually (FOC=D) before attempting to delete the main TN."),
52  : (762,"Unlock Attempted on an Unlocked TN (Same Company ID)","Unlock attempted on a TN that is already unlocked, and the Company ID on the service order matches the Company ID on the TN records."),
53  : (764,"Insert Attempted On A TN That Is Unlocked","Insert attempted on a TN that is unlocked. Once a TN record has been successfully unlocked  the only valid function of change is 'M' or migrate."),
54  : (765,"Change Attempted On A TN That Is Unlocked","Change attempted on a TN that is unlocked. Once a TN record has been successfully unlocked  the only valid function of change is 'M' or migrate."),
55  : (766,"Delete Attempted On A TN That Is Unlocked","Delete attempted on a TN that is unlocked. One a TN record has been successfully unlocked  the only valid function of change is 'M' or migrate."),
56  : (767,"Company IDs Do Not Match On A Change","Company IDs do not match on a change. The TN record that you are trying to change is assigned to a different Company ID. This record needs to be unlocked by the original Company and a migrate order processed by the new Company. Only after the migrate order has been successfully processed can change orders be applied."),
57  : (768,"Company IDs Do Not Match On A Delete","Company IDs do not match on a delete. The TN record that you are trying to delete is assigned to adifferent Company ID. This record needs to be unlocked by the original Company and a migrate order processed by the new Company. Only after the migrate order has been successfully processed can delete orders be applied."),
58  : (769,"Clerical and ERROR record Company IDs do not match.","Clerical and ERROR record Company IDs do not match. The Company Ids) associated with the clerical user do not match the Company ID of the ERROR  record. Either an additional Company ID needs to be assigned to the clerical user  or a different clerical user with the appropriate Company ID should process this record."),
59  : (770,"Clerical and TN record Company IDs do not match.","Clerical and TN record Company IDs do not match. The Company ID(s) associated with the clerical user do not match the Company ID of the TN record. Either an additional Company ID needs to be assigned to the clerical user  or a different clerical user with the appropriate Company ID should process this record."),
60  : (771,"Unlock Attempted On A Non-Existent TN","Unlock attempted on a nonexistent TN. The TN record that you are attempting to unlock does not exist."),
61  : (772,"Company IDs Do Not Match On Unlock","Company IDs do not match on an unlock. Only the Company ID associated with the TN record can unlock that TN record."),
62  : (773,"Migrate Attempted On A Non-Existent TN","Migrate attempted on a nonexistent TN. The TN record that you are trying to migrate does not exist."),
63  : (774,"Multiple MSAG matches found","Multiple MSAG matches found while evaluating aliases"),
64  : (819,"Subsidiary line unchanged","A change was made to this subsidiary line's main number.  This is an informational error.If the change should not be applied to the subsidiary line, this error record should be deleted."),
65  : (825,"Location comment flag set on a change (FOC=C).","Location comment flag set on a change  (FOC=C). An attempt was made to change a record that has the location comment (LocCom) flag set. This is an informational error. The service order was processed, but the location and telco comment fields were not changed."),
66  : (826,"Location comment flag set on a migrate (FOC=M).","Location comment flag set on a migrate. An attempt was made to migrate (FOC=M) a record that has the location comment (LocCom) flag set. This is an informational error. The service order was processed, but the location and telco comment fields were not changed."),
67  : (827,"Customer Name Changed in a Private Record.","A Private Record Was Deleted. A service order (FOC=D) was processed that deleted a record marked 'PRIVATE' in the database. This is an informational error.  Please determine whether  to remove or retain the 'PRIVATE' status for this TN."),
68  : (828,"A Private Record Was Deleted.","A Private Record Was Deleted. A service order (FOC=D) was processed that deleted a record marked 'PRIVATE' in the database. This is an informational error.  Please determine whether  to remove or retain the 'PRIVATE' status for this TN."),
69  : (833,"Location comment flag set on a delete.","Location comment flag set on a delete. A service order was processed that deleted a record that had the Location comment (LocCom) flag set. This is an informational error."),
70  : (863,"Migrate attempted on a record that is locked.","Migrate attempted on a record that is locked. An attempt was made to migrate a record that is not yet unlocked by the donor Company. This is an informational error. The service order (FOC=M) will be reprocessed automatically a limited number of times. If the record is still locked after that, no further attempts will be made and a 301 error will be generated."),
}

        
class SO_Form(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, u'SO Error Codes and descriptions')
        
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
        self.list_ctrl = SO_ListCtrl(self, size=(660, 455),
                         style=wx.LC_REPORT
                         |wx.BORDER_SUNKEN
                         |wx.LC_SORT_ASCENDING
                         )
        self.SetClientSize(wx.Size(660, 455))
        
        #self.list_ctrl.SetBackgroundColour(wx.Colour(255, 255, 128))     #yellow
        self.list_ctrl.SetBackgroundColour((255,228,196))  # bisque
        
        self.list_ctrl.InsertColumn(0, "Error Code")
        self.list_ctrl.InsertColumn(1, "Description", wx.LIST_FORMAT_LEFT)
        self.list_ctrl.InsertColumn(2, "Long Description", wx.LIST_FORMAT_LEFT)

        self.list_ctrl.SetColumnWidth(1, 260)
        self.list_ctrl.SetColumnWidth(2, 550)

        items = errdata.items()
        index = 0
        
        self.RowDict = {}     # dictionary for row data
        
        for key, data in items:
            self.list_ctrl.InsertStringItem(index, str(data[0]).strip())
            
            self.list_ctrl.SetStringItem(index, 1, data[1])
            self.list_ctrl.SetStringItem(index, 2, data[2])
            self.list_ctrl.SetItemData(index, key)
            self.RowDict[index] = data
            index += 1

        #print self.RowDict
 
        # Now that the list exists we can init the other base class,
        # see wx/lib/mixins/listctrl.py
        self.itemDataMap = errdata
        
        listmix.ColumnSorterMixin.__init__(self, 3)
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
##        print selItem[2]        # long_description
        
        wx.MessageBox(selItem[2], "Long description of  error code  %s\n\r" % selItem[0], wx.STAY_ON_TOP)


if __name__ == '__main__':
    app = wx.App(False)
    frame = SO_Form()           #using SO_Form    
    frame.Show()
    app.MainLoop()
