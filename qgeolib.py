#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  3 21:01:57 2025

qgeolib

PyQgis uyumlu geometri fonksiyonları modülü

Noktalar QgsPointXY objesi olacak şekilde düzenlendi. 

@author: Prof.Dr.İbrahim Öztuğ BİLDİRİCİ

Bilgi
1-QgsPointXY'lerden oluşan listelerde ilk nokta son nokta aynı olmamalı
  Polygon ya da Multipolygon geometrisinden elde edilen listede (geometry.asMultiPolygon)
  ilk nokta ve son nokta aynı olduğundan son nokta silinmeli (ls.pop())
  Bu yapılmazsa özellikle yan noktada problem çıkar. 
"""

from qgis.core import *
import qgis.utils
from qgis import processing
from PyQt5.QtCore import QVariant
from matplotlib import pyplot as plt
from math import pi,degrees
plt.axis("equal")
plt.rcParams['figure.dpi']=300
def triarea(p,q,r):
    "Üç noktadan oluşan üçgen alanı"
    return (p.x()*q.y()-p.y()*q.x()+q.x()*r.y()-q.y()*r.x()+r.x()*p.y()-r.y()*p.x())/2
def side(p,q,r):
    "Taraf operatörü, q pr nin sağında 1 solunda -1 üzerinde 0"
    a=triarea(p,q,r)
    return int((a>0)-(a<0))
def kes_ok(l1,l2):
    "l1 l2 kesişir mi? True/False"
    return side(l1[0],l1[1],l2[0])!=side(l1[0],l1[1],l2[1]) and \
           side(l2[0],l2[1],l1[0])!=side(l2[0],l2[1],l1[1])
           
def kesisim(p,q,pp,qp,param=0):
    "p-q pp-qp doğrularının kesişimi"
    pd=(pp.x()-qp.x())*(p.y()-q.y())-(p.x()-q.x())*(pp.y()-qp.y())
    if abs(pd)<=1e-14:    #Paralel olma durumu
        return None,False
    al=((q.x()-qp.x())*(pp.y()-qp.y())-(pp.x()-qp.x())*(q.y()-qp.y()))/pd
    be=((p.x()-q.x())*(qp.y()-q.y())-(qp.x()-q.x())*(p.y()-q.y()))/pd
    ara=al>=0 and al<=1 and be>=0 and be<=1
    if param==1:
        return ara      
    x=al*p.x()+(1-al)*q.x()
    y=al*p.y()+(1-al)*q.y()
    if param==2:
        return QgsPointXY(x,y),al,be
    return QgsPointXY(x,y),ara
   
def onson(i,n):
    "Nokta listelerinde bir önceki bir sonraki nokta bulma"
    if i>=n:
        return None
    ion=n-1 if i==0 else i-1
    isn=0 if i==n-1 else i+1
    return ion,isn

def dik(nk1,nk2,nk3):
    """1-2 doğrusuna 3 den inilen dik boy ve dik ayak
    dik ayak 1-2 arasında değilse ii>>False
    1-2 çakışık ise s=None h=None ii=False olur. 
    """
    k=nk1.distance(nk2)
    if k<1.e-14:
        # print("Dik hata!")
        # print(nk1,nk2,nk3)
        return None,None,False
    s=(nk2.x()-nk1.x())*(nk3.x()-nk1.x())/k+(nk2.y()-nk1.y())*(nk3.y()-nk1.y())/k
    h=(nk2.y()-nk1.y())*(nk3.x()-nk1.x())/k-(nk2.x()-nk1.x())*(nk3.y()-nk1.y())/k
    ii= s>1.e-14 and s<(k-1.e-14)
    return h,s,ii
def ynok(nk1,nk2,s,h):
    """Yan nokta, 1-2 doğrusunda dik ayak dik boydan koordinata geçiş"""
    k=nk1.distance(nk2)
    sn=(nk2.x()-nk1.x())/k
    cs=(nk2.y()-nk1.y())/k
    x=nk1.x()+s*sn+h*cs
    y=nk1.y()+s*cs-h*sn
    return QgsPointXY(x,y)

def poly_area(nkt):
    """Çokgen alanı liste ile çalışır.
    Nokta dizilimi saat ibresi yönünde ise pozitif! Değilse neg.
    """
    f=0
    for i in range(len(nkt)):
        f+=nkt[i].x()*nkt[i-1].y()-nkt[i].y()*nkt[i-1].x()
    return f/2

def poly_perim(nkt):
    "Çevre hesabı"
    c=0
    for i in range(len(nkt)):
        c+=nkt[i].distance(nkt[i-1])
    return c

def izoper(nkt):
    "izoperimetrik oran >0.95 ise şekil daire!"
    f=poly_area(nkt)
    c=poly_perim(nkt)
    return 4*pi*f/c**2

def is_circle(nkt,da=0.95):
    "izoperimetrik oran >= da ise True"
    izop=izoper(nkt)
    return izop>=da
    
def dikin(nok,dk=0.15):
    """Yakın noktalardan dik inme ...
    dk dik inme uzaklığı, dik dk dan küçükse araya nokta ekler. 
    """
    dk2=dk/4  #dik ayağının minimum uzaklığı
    nok2=[]
    n=len(nok)
    for i in range(n):
        ion,isn=onson(i,n)
        nok2.append(nok[i])
        ss=[]
        for j in range(n):
            #i,isn doğrusunun dışında ve devamı olmayan j gerekli
            if abs(i-j)<=1 or abs(isn-j)<=1:
                continue
            h,s,ii=dik(nok[i], nok[isn], nok[j])
            if ii and abs(h)<=dk and abs(s)>dk2:
                #print("s eklendi")
                ss.append(s)
        if len(ss)>0:
            ss.sort()
            for jj in range(len(ss)):
                if jj>0:
                    if abs(ss[jj]-ss[jj-1])<dk/10:
                        continue
                anok=ynok(nok[i],nok[isn],ss[jj],0)
                anok.m=1
                nok2.append(anok)
    return nok2    

def listdraw(nok,rnk='k',yaz=True,kapat=False):
    "QgsPointXY listesinin pyplot ile çizilmesi"
    plt.axis('equal')
    if isinstance(nok,list):
        x=[nk.x() for nk in nok]
        y=[nk.y() for nk in nok]
        plt.plot(x,y,c=rnk)
        if yaz:
            for i in range(len(x)):
                plt.annotate(i,(x[i],y[i]))
        if kapat:
            plt.plot((x[-1],x[0]),(y[-1],y[0]),c=rnk)

def pointdraw(p,rnk='k'):
    plt.scatter(p.x(),p.y(),marker='o',color=rnk)

def duzaci(p,q,r,da=1):
    """p q r doğrularının arasındaki 
    q'daki açının sapması da civarı mı? True/False, da birimi drc"""
    a1=p.azimuth(q)
    a2=q.azimuth(r)
    return abs(a2-a1)<=da

def dikaci(h,i,k,l,da=5):
    """h-i ve k-l doğruları dik mi?"""
    a=abs(h.azimuth(i)-k.azimuth(l))
    if a>180:
        a-=180
    return abs(a-90)<=da

def duzleaci(pol,da=5,inplace=False):
    """Çokgende bir noktadaki açı da'dan küçük ise noktayı siler.
    Açı birimi derece"""
    if inplace:
        poli=pol
    else:
        poli=pol.copy()
    while True:
        #print(len(poli))
        n=len(poli)
        for i in range(n):
            ion,isn=onson(i,n)
            a1=poli[ion].azimuth(poli[i])
            a2=poli[i].azimuth(poli[isn])
            daa=abs(a2-a1)
            if daa<=da or abs(daa-180)<=da:
                poli.pop(i)
                break
        if n==len(poli):
            break
    return poli

def nokort(*pnt):
    "Nokta listesinin ortalamasını alır. QgsPointXY olarak döndürür."
    x=[p.x() for p in pnt]
    y=[p.y() for p in pnt]
    return QgsPointXY(sum(x)/len(x),sum(y)/len(y))

def duzlekenar(pol,ds=0.05,inplace=False):
    """Çokgende bir kenar ds'den küçük ise kenarın ortasına nokta atar."""
    if inplace:
        poli=pol
    else:
        poli=pol.copy()
    while True:
        n=len(poli)
        for i in range(n):
            kn=poli[i].distance(poli[i-1])
            if kn<=ds:
                poli[i]=nokort(poli[i],poli[i-1])
                poli.pop(i-1)
                break
        if n==len(poli):    #for döngüsü list. değiştirmedi ise while'dan çık
            break
    return poli
def kirp(nokt,da=0.25,inplace=True):
    if inplace:
        nok=nokt
    else:
        nok=nokt.copy()
    "Verilen alan kriterine göre girinti ve çıkıntıları kırpar."
    # dk=da**0.5
    # ne=0
    while True:
        n=len(nok)       
        for j in range(n):
            i,k=onson(j,n)
            if duzaci(nok[i],nok[j],nok[k],da=2):
                continue
            a=triarea(nok[i],nok[j],nok[k])
            # print(j,a)
            if abs(a)<=da:  # and a<0.: #a<0 sadece çıkıntı 
                # ll,l=onson(k,n)
                # if dikaci(nok[i],nok[j],nok[k],nok[l]):
                #     continue
                nok.pop(j)
                # ne+=1
                break
        if n==len(nok):
            break
    return nok
def kose_duzle(nok,da=0.25,dk=0.5):
    "Verilen alan kriterine göre köşeleri ve içe girintileri kapatır"
    # daa=1e-5
    while True:
        n=len(nok)
        for j in range(n):
            if hasattr(nok[j],"m"):
                # print(j)
                continue
            i,k=onson(j,n)
            if duzaci(nok[i],nok[j],nok[k],da=2):
                continue
            a=triarea(nok[i],nok[j],nok[k])
            dji=nok[j].distance(nok[i])
            djk=nok[j].distance(nok[k])
            dik=nok[i].distance(nok[k])
            # print(j,a,dji,djk)
            if (abs(a)<=da or min(dji,djk,dik)<=dk )and a>0.: #pozitifse içe doğru
                ll,l=onson(k,n)
                h,hh=onson(i,n)
                ai=triarea(nok[j],nok[k],nok[l])
                # print(ai)
                if ai<0:     #bir sonraki nokta neg. dışa doğru
                    if dikaci(nok[h],nok[i],nok[k],nok[l]):
                        nok[j]=kesisim(nok[h],nok[i],nok[k],nok[l])[0]
                        if not hasattr(nok[i],"m"):
                            nok.pop(i)
                            break
                    else:
                        nok.pop(j)
                        break
                # elif abs(a)<=da and a>0.:
                else:
                    # print("sil",j,hasattr(nok[j],"m"))
                    nok.pop(j)
                    break
            elif abs(a)<=da and a<0: # or min(dji,djk)<=dk: dışa doğru çıkıntı ise
            # elif (abs(a)<=da or min(dji,djk,dik)<=dk ) and a<0: # or min(dji,djk)<=dk: dışa doğru çıkıntı ise
                nok.pop(j)
                break
        if n==len(nok):
            break
    return n

def kendikes(nok,check=False):
    "Kendi kendini kesen çokgenlere nokta atar."
    nok2=[]
    jj=0
    n=len(nok)
    for i in range(n):
        ion,isn=onson(i,n)
        nok2.append(nok[i])
        for j in range(n):
            jon,jsn=onson(j,n)
            if i==j or isn==j or i==jsn:
                continue
            # print(i,isn,"--",j,jsn)
            nkes,ii=kesisim(nok[i], nok[isn], nok[j], nok[jsn])                
            if ii:
                jj+=1
                nok2.append(nkes) 
    if check:
        return jj==0
    return nok2
def kendikes2(nok,da=1):
    "Kendi kendini kesen ... "
    noks=[]
    noks.append(nok)
    while True:
        jj=0
        n=len(nok)
        for i in range(n):
            ion,isn=onson(i,n)
            for j in range(n):
                brk=False
                jon,jsn=onson(j,n)
                if i==j or isn==j or i==jsn:
                    continue
                nkes,ii=kesisim(nok[i], nok[isn], nok[j], nok[jsn]) 
                # print(i,isn,"--",j,jsn,ii)               
                if ii:
                    nok2=[]
                    jj+=1
                    nok2.append(nkes)
                    k=isn
                    while True:
                        nok2.append(nok[k])
                        kk,k=onson(k,n)
                        if k==jsn:
                            break
                    a=abs(poly_area(nok2))
                    # print(a,len(nok2),i,isn,j,jsn)
                    if a>=da:
                        noks.append(nok2)
                    k=isn
                    nok[j]=nkes
                    while k<j:
                        nok.pop(isn)
                        k+=1
                    brk=True
                    break
            if brk:
                break
        if n==len(nok):
            break
    if poly_area(nok)<=da:
        noks.pop(0)
    return noks
import random
def daireyap(p0,r,dr=1,noise=False):
    ring=[]
    da=degrees(dr/r)
    #Yaya karşılık açı 30'den büyükse daire görünümünü korumak için 30
    #yapıyoruz, ki daire min 12 noktadan oluşsun. 
    if da>30:
        da=30
    az=0
    while az<360:
        if noise:
            r+=random.uniform(-dr/5,dr/5)
        ring.append(p0.project(r,az)) #project birinci temel ödev!
        az+=da
    return ring
def makeRect(geom, tol1=0.95,tol2=0.95,dr=1):
    "tol1 dikdörtgen, tol2 daire için tolerans"
    area0=abs(geom.area())
    ci=4*pi*area0/geom.length()**2
##    print(ci,area0,geom.length())
    geom2, area, angle, width, height = geom.orientedMinimumBoundingBox()
    aort=area0/area 
    # print(ci)
    if ci>=tol2 and ci <0.9999:
        r=(area0/pi)**0.5
        p0=geom.centroid().asPoint()
        rng=daireyap(p0,r,dr=dr)
        return QgsGeometry.fromPolygonXY([rng])
    elif aort>=tol1 and aort <0.9999:
        return geom2
    else:
        return None
def sekilYap(lyr,tolR=0.95,tolC=0.95,dr=1,da=5,a_ele=True):
    crs=lyr.crs()
    vl = QgsVectorLayer("MultiPolygon", "SekilYap", "memory")
    vl.setCrs(crs)
    pr = vl.dataProvider()
    # Mevcut kolonları taşıma
    pr.addAttributes(lyr.fields()) 
    vl.updateFields()
    for ft in lyr.getFeatures():
        geom=ft.geometry()
        #ilk şeklin alanı küçükse vd a_ele true ise elimine et. 
        if geom.area()<=da and a_ele:
            continue
        if geom.isMultipart():
            plgn = geom.asMultiPolygon()
        else: 
            plgn = [geom.asPolygon()]
        for i in range(len(plgn)):
            for j in range(len(plgn[i])):
                geom0=QgsGeometry.fromPolygonXY([plgn[i][j]])
                a0=geom0.area()
                #alt ring küçükse
                if a0<=da:
                    plgn[i][j]=None
                    continue
                geom1=makeRect(geom0,tol1=tolR,tol2=tolC,dr=dr)
                if geom1:
                    plgn[i][j]=geom1.asPolygon()[0]
            #Yukarıda None yapılanları atalım. 
            plgn[i]=[ii for ii in plgn[i] if ii]
        geomN=None
        for i in range(len(plgn)):
            if i==0:
                geomN=QgsGeometry.fromPolygonXY(plgn[i])
            elif geomN:
                geomi=QgsGeometry.fromPolygonXY(plgn[i])
                geomN.addPartGeometry(geomi)
        fet  = QgsFeature()
        fet.setGeometry(geomN)
        attr=[ft[i] for i in range(len(lyr.fields()))]
        fet.setAttributes(attr)
        pr.addFeatures([fet])
    vl.updateFields()
    return vl
def sekilYap2(lyr,tolR=0.95,tolC=0.95,\
              dr=1,da=5,daci=3,daln=0.8,dknr=5,kongen=True):
    crs=lyr.crs()
    if kongen:
        lyrname="Genelleştirilmiş"
    else:
        lyrname="Dörtgen/daireleştirilmiş"
    vl = QgsVectorLayer("MultiPolygon", lyrname, "memory")
    vl.setCrs(crs)
    pr = vl.dataProvider()
    # Mevcut kolonları taşıma
    pr.addAttributes(lyr.fields()) 
    vl.updateFields()
    for ft in lyr.getFeatures():
        geom=ft.geometry()
        #ilk şeklin alanı küçükse elimine et. 
        if abs(geom.area())<=da:
            continue
        if geom.isMultipart():
            plgn = geom.asMultiPolygon()
        else: 
            plgn = [geom.asPolygon()]
        for i in range(len(plgn)):
            for j in range(len(plgn[i])):
                geom0=QgsGeometry.fromPolygonXY([plgn[i][j]])
                a0=abs(geom0.area())
                #alt ring küçükse
                if a0<=da:
                    plgn[i][j]=None
                    continue
                geom1=makeRect(geom0,tol1=tolR,tol2=tolC,dr=dr)
                if geom1:    #geometri daire/dörtgen yapıldıysa
                    plgn[i][j]=geom1.asPolygon()[0]
                else:        #Geometri değişmediyse kontur gen yap.  
                    if kongen:
                        plgn[i][j]=konturGenPol(plgn[i][j],daci=daci,daln=daln,dknr=dknr)
            #Yukarıda None yapılanları atalım. 
            plgn[i]=[ii for ii in plgn[i] if ii]
        geomN=None
        for i in range(len(plgn)):
            if i==0:
                geomN=QgsGeometry.fromPolygonXY(plgn[i])
            elif geomN:
                geomi=QgsGeometry.fromPolygonXY(plgn[i])
                geomN.addPartGeometry(geomi)
        fet  = QgsFeature()
        fet.setGeometry(geomN)
        attr=[ft[i] for i in range(len(lyr.fields()))]
        fet.setAttributes(attr)
        pr.addFeatures([fet])
    vl.updateFields()
    return vl
def konturGenPol(qnok,daci=3,daln=0.8,dknr=5):
    #İlk ve son nokta bu fonksiyonlarda aynı olmamalı!
    #4 nokta ve az ise genelleştirme yapmamalı
    if len(qnok)<=4:
        return qnok
    qnok.pop()
    duzleaci(qnok,da=daci,inplace=True)
    qnokd=dikin(qnok,dk=dknr)
    kirp(qnokd,da=daln,inplace=True)
    duzleaci(qnokd,da=daci,inplace=True)
    kose_duzle(qnokd,da=daln,dk=dknr)
    duzleaci(qnokd,da=daci,inplace=True)
    #İlk ve son noktayı aynı yapıp döndürelim. 
    if len(qnokd)>=3:
        qnokd.append(qnokd[0])
        return qnokd
    else:
        return qnok
def konturGen(lyr,daci=3,daln=0.8,dknr=5,dA=10):
    crs=lyr.crs()
    vl = QgsVectorLayer("MultiPolygon", "Kontur Genelleştirme", "memory")
    vl.setCrs(crs)
    pr = vl.dataProvider()
    # Mevcut kolonları taşıma
    pr.addAttributes(lyr.fields()) 
    vl.updateFields()
    for ft in lyr.getFeatures():
        geom=ft.geometry()
        #ilk şeklin alanı küçükse elimine et. 
        if geom.area()<=dA:
            continue
        if geom.isMultipart():
            plgn = geom.asMultiPolygon()
        else: 
            plgn = [geom.asPolygon()]
        for i in range(len(plgn)):
            for j in range(len(plgn[i])):
                geom0=QgsGeometry.fromPolygonXY([plgn[i][j]])
                a0=geom0.area()
                #alt ring küçükse
                if a0<=dA:
                    plgn[i][j]=None
                    continue
                plgn[i][j]=konturGenPol(plgn[i][j],daci=daci,daln=daln,dknr=dknr)
            #Yukarıda None yapılanları atalım. 
            plgn[i]=[ii for ii in plgn[i] if ii]
        geomN=None
        for i in range(len(plgn)):
            if i==0:
                geomN=QgsGeometry.fromPolygonXY(plgn[i])
            elif geomN:
                geomi=QgsGeometry.fromPolygonXY(plgn[i])
                geomN.addPartGeometry(geomi)
        fet  = QgsFeature()
        fet.setGeometry(geomN)
        attr=[ft[i] for i in range(len(lyr.fields()))]
        fet.setAttributes(attr)
        pr.addFeatures([fet])
    vl.updateFields()
    return vl
def birlestir(lyr,bdist=2):
    #Buffer aşaması
    params0={
    'INPUT':lyr,
    'DISTANCE':bdist,
    'SEGMENTS':5,
    'END_CAP_STYLE':0,
    'JOIN_STYLE':1,
    'MITER_LIMIT':2,
    'DISSOLVE':False,
    'OUTPUT':'memory:'}
    lyr1 = processing.run("native:buffer", params0)['OUTPUT']
    #Birleştirme aşaması
    params1 = {
    'INPUT': lyr1,
    'OUTPUT': 'memory:', 
    'FIELD': [],  # You can specify field names to dissolve based on specific attributes
    'GEOMETRY': None,
    'SEPARATE_DISJOINT':True}
    lyr2=processing.run('native:dissolve', params1)['OUTPUT']
    #Ters buffer
    params3={
    'INPUT':lyr2,
    'DISTANCE':-bdist,
    'SEGMENTS':5,
    'END_CAP_STYLE':0,
    'JOIN_STYLE':1,
    'MITER_LIMIT':2,
    'DISSOLVE':False,
    'OUTPUT':'memory:'}
    lyr3 = processing.run("native:buffer", params3)['OUTPUT'] 
    #Parçalama
    params2 = {
    'INPUT': lyr3,
    'OUTPUT': 'memory:',
    'FIELD': [], 
    'GEOMETRY': None}
    lyr4=processing.run('native:multiparttosingleparts', params2)['OUTPUT']
    lyr4.setName('Birleştirilmiş')   
    return lyr4
def alan_eleme(lyr,a1=25,a2=156):
# Alan katmanında a1 den küçükleri siliyor. a2 den küçükleri ise
# küçükbina katmanına alıyor. 
    iar=False
    ian=False
    crs=lyr.crs()
    vl = QgsVectorLayer("Point", "Kucukbina", "memory")
    vl.setCrs(crs)
    pr = vl.dataProvider()
    # Mevcut kolonları taşıma
    pr.addAttributes(lyr.fields()) 
    field_names = [field.name() for field in lyr.fields()]
    if "Area" not in field_names:
        pr.addAttributes([QgsField("Area", QVariant.Double)])
        iar=True
    if "Angle" not in field_names:
        pr.addAttributes([QgsField("Angle", QVariant.Double)])
        ian=True
    vl.updateFields()
    idx_ar=vl.fields().indexOf('Area')
    idx_an=vl.fields().indexOf('Angle')
    #print(idx_ar,idx_an)
    for ft in lyr.getFeatures():
        geom=ft.geometry()
        #Alan küçükse ...
        if geom.area()<=a2:
            if geom.area()>=a1:
                fp=QgsFeature()
                geom2, area, angle, width, height = geom.orientedMinimumBoundingBox()
                fp.setGeometry(geom.centroid())
                attr=[ft[i] for i in range(len(lyr.fields()))]
                if iar:
                    attr.append(geom.area())
                else:
                    attr[idx_ar]=geom.area()
                if ian:
                    attr.append(angle)
                else:
                    attr[idx_an]=angle
                fp.setAttributes(attr)
                pr.addFeatures([fp])
            #şimdi alanı silelim
            lyr.dataProvider().deleteFeatures([ft.id()])
            lyr.updateFeature(ft)
    lyr.commitChanges() 
    lyr.updateExtents()    
    vl.commitChanges() 
    vl.updateExtents()
    return vl    

if __name__=='__main__':
    # p0=QgsPointXY(5,3)
    # qnok=daireyap(p0, 3,dr=0.5,noise=True)
    # listdraw(qnok,yaz=False,kapat=True)
    # geom=QgsGeometry.fromPolygonXY([qnok])
    # geom2=makeRect(geom,dr=1)
    # plgn=geom2.asPolygon()[0]
    # listdraw(plgn,yaz=False,rnk='r',kapat=True)
    plt.axis("off")
    plt.axis("equal")
    # nok=[(457135.54697846435, 4206563.737425049, 0), (457147.2943098381, 4206564.827674474, 0), (457147.310808899, 4206564.587619554, 0), (457146.3703624267, 4206564.49759896, 0), (457146.89833237603, 4206558.766287765, 0), (457147.84702837886, 4206558.856308359, 0), (457147.8717769702, 4206558.606251151, 0), (457146.92308096745, 4206558.526232845, 0), (457147.20356500306, 4206555.485537202, 0), (457148.15226100583, 4206555.575557797, 0), (457148.1770095972, 4206555.32550059, 0), (457147.2283135944, 4206555.235479995, 0), (457147.50879763, 4206552.194784352, 0), (457148.4574936328, 4206552.284804947, 0), (457148.4822422242, 4206552.034747739, 0), (457147.5335462214, 4206551.954729432, 0), (457147.73978448287, 4206549.764228296, 0), (457148.68023095524, 4206549.844246602, 0), (457148.7049795466, 4206549.594189394, 0), (457147.7562835438, 4206549.514171087, 0), (457148.0615161708, 4206546.273429679, 0), (457149.0019626431, 4206546.363450273, 0), (457149.0267112345, 4206546.1133930655, 0), (457148.08626476215, 4206546.023372471, 0), (457148.58948612015, 4206540.552120771, 0), (457149.538182123, 4206540.642141366, 0), (457149.56293071434, 4206540.392084159, 0), (457148.61423471157, 4206540.302063564, 0), (457148.9112178081, 4206537.061322155, 0), (457149.85991381085, 4206537.15134275, 0), (457149.88466240227, 4206536.901285542, 0), (457148.93596639944, 4206536.821267236, 0), (457149.1422046609, 4206534.630766098, 0), (457150.0909006637, 4206534.710784405, 0), (457150.10739972466, 4206534.460727197, 0), (457149.1669532523, 4206534.380708891, 0), (457149.4474372879, 4206531.340013248, 0), (457150.38788376027, 4206531.430033843, 0), (457150.4126323516, 4206531.179976636, 0), (457149.4721858793, 4206531.0899560405, 0), (457149.7526699149, 4206528.0592626855, 0), (457150.69311638724, 4206528.139280993, 0), (457150.7178649786, 4206527.899226073, 0), (457149.7774185063, 4206527.809205478, 0), (457150.3053884556, 4206522.0778942825, 0), (457151.25408445846, 4206522.167914878, 0), (457151.27058351936, 4206521.91785767, 0), (457139.5232521456, 4206520.827608245, 0), (457139.47375496285, 4206521.237702066, 0), (457139.70474181575, 4206521.09767003, 0), (457139.1685223359, 4206526.818978936, 0), (457138.97053360485, 4206526.808976648, 0), (457138.9457850135, 4206527.049031568, 0), (457139.1437737445, 4206527.069036144, 0), (457138.8632897089, 4206530.109731787, 0), (457138.6653009779, 4206530.089727211, 0), (457138.6405523865, 4206530.339784418, 0), (457138.846790648, 4206530.359788994, 0), (457138.5580570819, 4206533.390482349, 0), (457138.3600683509, 4206533.370477772, 0), (457138.3353197595, 4206533.620534981, 0), (457138.541558021, 4206533.640539557, 0), (457138.3353197595, 4206535.831040694, 0), (457138.1373310285, 4206535.811036117, 0), (457138.1125824371, 4206536.061093325, 0), (457138.9622840744, 4206536.141111632, 0), (457137.80734981014, 4206548.583958276, 0), (457136.95764817286, 4206548.503939969, 0), (457136.93289958144, 4206548.753997177, 0), (457137.1308883125, 4206548.774001754, 0), (457136.93289958144, 4206550.964502891, 0), (457136.72666132, 4206550.9444983145, 0), (457136.71016225906, 4206551.194555522, 0), (457136.9081509901, 4206551.214560099, 0), (457136.6276669545, 4206554.255255741, 0), (457136.42967822345, 4206554.235251165, 0), (457136.4049296321, 4206554.485308372, 0), (457136.6029183631, 4206554.5053129485, 0), (457136.3224343275, 4206557.5360063035, 0), (457136.1244455965, 4206557.516001727, 0), (457136.0996970051, 4206557.766058935, 0), (457136.29768573615, 4206557.786063511, 0), (457135.7614662563, 4206563.507372418, 0), (457135.56347752525, 4206563.487367841, 0), (457135.54697846435, 4206563.737425049, 0)]
    # nok=[(456654.8799569647, 4202935.7678494165), (456655.8612543912, 4202934.6280528605), (456655.74580798915, 4202934.5280704), (456654.7645105639, 4202935.667866959), (456654.69029501395, 4202935.607877477), (456653.5193350617, 4202936.967634775), (456650.90529867867, 4202934.7180293985), (456652.0762586306, 4202933.358272097), (456644.9515664045, 4202927.229347221), (456645.2814142735, 4202926.84941504), (456645.0505214717, 4202926.649450118), (456644.7289197842, 4202927.029382313), (456637.6042275588, 4202920.900457436), (456636.4332676066, 4202922.260214735), (456633.8192312241, 4202920.0106093595), (456634.990191176, 4202918.650852061), (456634.91597562557, 4202918.590862576), (456635.8890268698, 4202917.451066002), (456635.78182665043, 4202917.351083554), (456621.3344897512, 4202934.138087289), (456629.06939868146, 4202940.786920976), (456629.7208482363, 4202940.0270566), (456631.91432986764, 4202941.916725111), (456630.9330324418, 4202943.056521673), (456631.1639252589, 4202943.246488364), (456632.1452226695, 4202942.116690031), (456634.3387043002, 4202944.006358545), (456633.6872547431, 4202944.766222925), (456641.4139174916, 4202951.4150565965), (456654.8799569647, 4202935.7678494165)]
    # nok=[(456848.9211140933, 4202776.9362857845), (456848.4427562253, 4202829.217021867), (456846.43893379916, 4202829.297004653), (456846.61213227303, 4202810.410351287), (456819.12760698184, 4202810.160353899), (456818.6739924464, 4202859.281649818), (456825.7904476837, 4202859.351648208), (456825.72446700337, 4202866.750337196), (456847.2881878999, 4202896.995011103), (456868.662315602, 4202881.74774505), (456872.66996650334, 4202877.598486299), (456874.8634562631, 4202874.129104338), (456876.42199046776, 4202870.3397781), (456877.4527714018, 4202864.9707309585), (456877.625969874, 4202846.084077589), (456875.58091696125, 4202845.884109918), (456875.71288077824, 4202829.4670189265), (456877.77442632616, 4202829.487018508), (456878.2527841922, 4202777.206282427), (456848.9211140933, 4202776.9362857845)]
    # nok=[(457039.3574533113, 4204780.319419013), (457047.2522539607, 4204782.33988125), (457046.7490326027, 4204784.270322892), (457056.6319700927, 4204786.800901831), (457057.12694192026, 4204784.87046019), (457065.0217425696, 4204786.890922426), (457068.01632212626, 4204775.218251981), (457057.25893440755, 4204772.467622698), (457057.50642032136, 4204771.497400734), (457057.5559175041, 4204770.667210804), (457057.2919325294, 4204769.887032317), (457057.01969802426, 4204769.51694765), (457056.4339813617, 4204769.066844677), (457055.55128160253, 4204768.816787469), (457054.7345780871, 4204768.92681264), (457053.81888020615, 4204769.536952227), (457053.34865696996, 4204770.427155886), (457053.09292152576, 4204771.3973778505), (457042.352032868, 4204768.63674628), (457039.3574533113, 4204780.319419013)]
    # nok=[(456475.19681380555, 4205477.248860837), (456489.0395259159, 4205480.029496984), (456488.93228201993, 4205480.589625129), (456490.6894320077, 4205480.869689201), (456491.9681092289, 4205473.788069085), (456480.8972393528, 4205471.887634308), (456476.6982283491, 4205471.187474128), (456475.19681380555, 4205477.248860837)]
    # nok=[(457862.8833304509, 4204804.604975004), (457869.02923064295, 4204804.594972716), (457869.02923064295, 4204804.885039076), (457872.6342754536, 4204804.885039076), (457872.6260259231, 4204803.484718715), (457877.02423574683, 4204803.474716426), 
          # (457877.02423574683, 4204803.074716426),(457877.72423574683, 4204803.074716426),
          # (457877.7159862164, 4204799.273755341), (457871.91656630364, 4204799.283757629), (457871.9083167732, 4204796.233059698), (457875.0596374085, 4204796.323080292), (457875.8103446803, 4204796.323080292), (457875.8103446803, 4204796.073023085), (457875.30712332233, 4204796.073023085), (457875.30712332233, 4204793.22237092), (457876.8002883354, 4204793.22237092), (457876.8002883354, 4204790.0716501055), (457876.2970669774, 4204790.0716501055), (457876.2970669774, 4204790.171672988), (457871.14935997094, 4204790.181675277), (457871.1411104405, 4204787.190991075), (457875.0431383476, 4204787.200993364), (457875.0431383476, 4204786.950936155), (457871.1411104405, 4204786.990945309), (457863.74128161866, 4204786.98094302), (457862.84208279866, 4204786.98094302), (457862.84208279866, 4204787.231000228), (457863.74128161866, 4204787.231000228), (457863.74953114917, 4204791.201908683), (457862.8503323291, 4204791.201908683), (457862.85858185956, 4204794.952766795), (457863.0070734078, 4204794.952766795), (457863.01532293827, 4204797.45333887), (457862.86683139, 4204797.45333887), (457862.8833304509, 4204804.604975004)]
    nok=[(456857.67875520757, 4202648.039137319), (456866.2712489007, 4202666.685846485), (456865.71866349236, 4202726.815191806), (456859.5752577562, 4202726.755193122), (456859.50927692524, 4202734.253864391), (456854.70999887685, 4202734.213864201), (456854.6852564784, 4202736.7534142), (456852.73915746703, 4202736.743413021), (456852.66493069514, 4202744.082112624), (456847.7172213646, 4202744.042112208), (456847.7007250572, 4202746.641651594), (456845.5979485967, 4202746.6216519475), (456845.5072249713, 4202756.919827159), (456878.44247669785, 4202757.219823952), (456879.1847557455, 4202676.354153017), (456878.8136809085, 4202674.1345457295), (456878.47558964643, 4202672.674803856), (456878.0632826991, 4202671.2450565575), (456877.56851391325, 4202669.825307361), (456877.0077756092, 4202668.445550979), (456876.69442172704, 4202667.755672739), (456865.850727599, 4202644.269817568), \
         (456857.67875520757, 4202648.039137319)]
    # nok.pop()
    qnok=[QgsPointXY(p[0],p[1]) for p in nok]
    # print(len(qnok))
    # qnokd=konturGenPol(qnok,daci=3,daln=12,dknr=5)
    # listdraw(qnokd,yaz=True,rnk='r',kapat=True)
    
    # duzleaci(qnok,da=3,inplace=True)
    # qnokd=dikin(qnok,dk=5)
    # kirp(qnokd,da=0.8,inplace=True)
    # duzleaci(qnokd,da=3,inplace=True)
    # kose_duzle(qnokd,da=0.5,dk=2.5)
    # duzleaci(qnokd,da=3,inplace=True)
    # qnokd=konturGenPol(qnok,daci=3)
    # qnokd=dikin(qnok,dk=0.5)
    # listdraw(qnokd,yaz=True)
    # kirp(qnokd,da=1,inplace=True)
    # duzleaci(qnokd,da=5,inplace=True)
    # duzlekenar(qnokd,ds=5,inplace=True)
    # duzleaci(qnokd,da=5,inplace=True)
    # listdraw(qnokd,yaz=True,kapat=True)
    # qnoks=duzleaci(qnokd,da=5)
    # kose_duzle(qnokd,da=12,dk=5)
    # listdraw(qnokd,kapat=True)
    # # qnokk=duzlekenar(qnoks,ds=0.2)
    # # listdraw(qnokk)
    # for j in range(len(qnoks)):
    #     i,k=onson(j,len(qnoks))
    #     print(j,triarea(qnoks[i],qnoks[j],qnoks[k]))
    nok=[(456783.1577630704, 4202807.940692629), (456786.1593734052, 4202807.960693635), (456786.12638329074, 4202811.5100647025), (456792.02240355883, 4202811.570063014), (456792.03065110656, 4202810.670222461), (456795.9805723919, 4202810.700223138), (456795.9723248445, 4202811.60006369), (456800.1696315843, 4202811.640062967), (456800.20262093854, 4202808.590603326), (456802.0497657482, 4202808.610602584), (456802.2147169961, 4202790.413826974), (456801.0684976692, 4202790.403827006), (456801.09324038646, 4202787.654314208), (456785.0956469005, 4202787.514314751), (456785.0709034242, 4202790.763738973), (456783.31446662056, 4202790.743739853), (456783.1577630704, 4202807.940692629)]
    nok.pop()
    qnok=[QgsPointXY(p[0],p[1]) for p in nok]
    kose_duzle(qnok,da=10,dk=5)
    listdraw(qnok,kapat=True)
    