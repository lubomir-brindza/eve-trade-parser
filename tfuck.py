#!/usr/bin/python

# tradeFucker 2000 v0.5 by Halka
# parses .txt files (eve online market dumps)

import os, sys
import time                                                            # for benchmarking

path = '.'
maxdev = 1.2                                                            # max deviation of sell price (for sell order grouping)
capacity = 167.0                                                        # capacity of ship's cargo hold - m^3
minmargin = 500000                                                      # minimal trip revenue

tmp=[]; master=[]; tmaster=[]; buy=[]; sell=[]; filelist=[]; items=[]; 

def icn(x):
  return int(float(x))

def formatnames(x,y):                                                 # compact output of item/region names
  word=''
  words=x.split(' ')
  for i in range(0,len(words)):
    words[i] = words[i][:y/len(words)]
  for n in range(0,len(words)):
    word = word + words[n][:y]
  return word 
  
def inside(value,arr,idx):                                            # check, if at least one field contains 'value'
  for i in range(0,len(arr)):                                         # (in a 2-dimm. array 'arr'. column index 'idx')
    if arr[i][idx] == value:
      return True
  return False
  
try:  
  idb = open('_items.csv').readlines()                                 # itemName;itemID;itemVolume
  for line in idb:
    items.append(line.replace('\n','').split(';'))
  idb = None
except: pass
  
print "Reading files:"
t_start = time.time()
for root, dirs, files in os.walk(path):
  for filename in files:
    if filename[-4:]=='.txt':
      tmp = filename[:-4].split('-')
      if filename.count('-') > 2:                                      # some region/item names contain '-'
        tmp[1] = '-'.join(tmp[1:-1])                                   # assuming item
        tmp[2] = tmp[-1]
        tmp[3] = ''
      if len(filelist) == 0:
        filelist.append(tmp)
      elif (filelist[-1][0] == tmp[0]) and (filelist[-1][1] == tmp[1]): 
        if filelist[-1][2] < tmp[2]:                                   # using the latest dump
          filelist[-1] = tmp
      else: 
        filelist.append(tmp)
t_end = time.time()
print "take ", t_end - t_start,"s"

print "Generating items list:"
t_start = time.time()
for file in filelist:
  file[2] = file[2]+'.txt'
  filename = '-'.join(file[:3])
  file[2] = file[2][:-4]
  f = open(filename).readlines()
  for line in f:
    if line[:5] == 'price': continue                                  # skipping first line of the dump (headers)
    tmplist = (line.replace('\n','').split(',')+file)
    master.append(tmplist)
    if not inside(tmplist[2],items,1):
      items.append((file[1],tmplist[2],'1.0'))    
t_end = time.time()
print "take ", t_end-t_start,"s "


idb = open('_items.csv','w')
items.sort()
for line in items:
  idb.write(';'.join(line)+'\n')
idb.close()

volumes = {}                                                            # load item volumes
for item in items:
  volumes[item[1]] = float(item[2])  

"Make master:"
t_start = time.time()
tmp = master[0]
# sell order grouping
tcena = float(master[0][0])
for i in range(1,len(master)):
  if ((master[i][7] == 'False') and (tmp[7] == 'False') and (tmp[2] == master[i][2]) and (tmp[15] == master[i][15]) and (float(master[i][0]) < (float(tcena)*maxdev)) and (float(master[i][0]) >= float(tcena))):
    tmp[0] = (float(tmp[0])*float(tmp[1]) + float(master[i][0])*float(master[i][1])) / (float(tmp[1]) + float(master[i][1]))
    tmp[1] = float(tmp[1]) + float(master[i][1])
  elif ((master[i][7] == 'True') and (tmp[7] == 'True') and (tmp[2] == master[i][2]) and (tmp[15] == master[i][15]) and (float(master[i][0]) > (float(tcena)/maxdev)) and (float(master[i][0]) <= float(tcena))):
    tmp[0] = (float(tmp[0])*float(tmp[1]) + float(master[i][0])*float(master[i][1])) / (float(tmp[1]) + float(master[i][1]))
    tmp[1] = float(tmp[1]) + float(master[i][1])  
  else:
    tmaster.append(tmp)
    tmp = master[i]
    tcena = master[i][0]
t_end = time.time()
print "takes ", t_end-t_start,"s"

master = tmaster
    
for i in master:
    # Tu je zmena - pripravime narocne konverzie mimo hlavneho cyklu
    i[0] = icn(i[0])
    i[1] = icn(i[1])
    i[15] = formatnames(i[15],8)
    i[16] = formatnames(i[16],14)                                      # Last data element
    i = i + [int(capacity/volumes[i[2]])]
    if i[7] == 'False':
        sell.append(i)
    elif i[7] == 'True':
        buy.append(i)

# groupedMaster = {"ItemID":{"sell":[],"buy":[]},....}

groupedMaster = {}

for item in sell:
    if item[2] in groupedMaster.keys():
        groupedMaster[item[2]]['sell'].append(item)
    else:
        groupedMaster[item[2]] = {'sell':[item],'buy':[]}

for item in buy:
    if item[2] in groupedMaster.keys():
        groupedMaster[item[2]]['buy'].append(item)
    else:
        groupedMaster[item[2]] = {'sell':[],'buy':[item]}

print "Found %d distinct item types" % len(groupedMaster)

print "Buy list length: ", len(buy)
print "Sell list length: ", len(sell)
print "Total cycles: ",len(buy)*len(sell)

print "Main cycle: "

t_start = time.time()
print('item type               buy orders    region           sell orders    region       trip profit      date dumped') # header    

realIterations = 0
combCount = 0
for itemType in groupedMaster.keys():
    for sellItem in groupedMaster[itemType]['sell']:
        for buyItem in groupedMaster[itemType]['buy']:
            realIterations += 1
            if (sellItem[0] < buyItem[0]*0.9):
                combCount += 1
                # margin for a single trip - min(#sell, #buy, #capacity/item volume)
                margin = (buyItem[0] - sellItem[0])*min(sellItem[1],buyItem[1],buyItem[17])*0.99  
                if margin > minmargin:
                    print('%-14s: %28s' % (sellItem[16], ' '.join((str(sellItem[1]), 'x', str(sellItem[0]),'isk ['+sellItem[15]+']')))),
                    print('>>'),
                    print('%28s %17s' % (' '.join((str(buyItem[1]),'x',str(buyItem[0]),'isk ['+buyItem[15]+']')), '('+str(margin)+' isk)')),
                    print(' ... '+buyItem[-2]+' - '+sellItem[-2])

t_end = time.time()
print "takes ",t_end-t_start,"s"

print "%d iterations complete" % realIterations
print "I have %d valid combinations" % combCount

