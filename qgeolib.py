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
def sekilYap(lyr,tolR=0.95,tolC=0.95,dr=1,da=5):
    crs=lyr.crs()
    vl = QgsVectorLayer("MultiPolygon", "SekilYap", "memory")
    vl.setCrs(crs)
    pr = vl.dataProvider()
    # Mevcut kolonları taşıma
    pr.addAttributes(lyr.fields()) 
    vl.updateFields()
    for ft in lyr.getFeatures():
        geom=ft.geometry()
        #ilk şeklin alanı küçükse elimine et. 
        if geom.area()<=da:
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
        if geom.area()<=da:
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
    pass
