# from .compre_lib import * 
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
import qgis.utils
from PyQt5 import uic
import os
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'main.ui'))
from . qgeolib import *
import time

class BGDialog(QDialog, FORM_CLASS):
    def __init__(self, iface,parent=None):
        """Constructor."""
        super(BGDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface=iface
        # self.params={"da1":0.,"da2":0.,"da3":0,"daci":0,"dknr":0,\
                     # "dknr":0.,"TolDo":1.,"TolDa":1.,"dtamp":1,\
                     # "sekil":False,"kongen":False}
        self.params={}
        # self.parametre_al()
        self.katman_al()
        self.buttonBox.clicked.connect(self.uygula)
        self.bilgi.setText("Açıldı")
        self.mesaj=""
        self.textMsg.setPlainText(time.strftime("%Y-%m-%d", time.localtime()))
        self.t0=time.time
    def parametre_al(self):
        #Program parametreleri ve işlemleri...
        self.params["da1"]=float(self.da1.text())           #Minimum alan (elenecek alanlar)
        self.params["da2"]=float(self.da2.text())           #Minimum alan (noktaya dönüşecek)
        self.params["da3"]=float(self.da3.text())           #Min alan (Kongen:Kontur genelleştirmesi için)
        self.params["daci"]=float(self.daci.text())         #Min açı (Kongen)
        self.params["dknr"]=float(self.dknr.text())         #Min kenar (Kongen)
        self.params["TolDo"]=float(self.TolDo.text())       #Dörgenleşme oranı
        self.params["TolDa"]=float(self.TolDa.text())       #Daireleşme Oranı
        self.params["dtamp"]=float(self.dtamp.text())       #Tampon uzaklığı (Birleştirme)
        self.params["sekil"]=self.SekilBox.isChecked()      #Birleştirme öncesi şekil yapılacak mı?
        self.params["kongen"]=self.KongenBox.isChecked()    #Birleştirme sonrası 
        self.params["minK"]=float(self.dknr.text())/2       #Daireleştirmede kiriş uzaklığı (qgeolib/daireyap daki açıklamaya bkz)
        # print(self.params)
    def katman_al(self):
        katmanlar=[]
        for lyr in self.iface.mapCanvas().layers():
            if lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                katmanlar.append(lyr.name())
        if len(katmanlar)>0:
            self.comboBox_layer.clear()
            self.comboBox_layer.addItems(katmanlar)
    @staticmethod
    def mesaj_yap(m,x):
        txt=f"{m:<18s}:"
        if isinstance(x,int):
            txt+=f"{x:<5d}"
        if isinstance(x,float):
            txt+=f"{x:<5.1f}"
        txt+='\n'
        return txt
    def kopyala(self):
        icerik = self.textMsg.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(icerik)
    
    def uygula(self):
        self.parametre_al()
        self.t0=time.time()
        self.mesaj="BuGen Oturumu\n"
        self.mesaj+=time.strftime("%Y-%m-%d", time.localtime())+" "
        self.mesaj+=time.strftime("%H-%M-%S", time.localtime())
        self.mesaj+='\n'
        #İşleme alınacak katmanı bulalım.
        for lyr in self.iface.mapCanvas().layers():
            if self.comboBox_layer.currentText()==lyr.name():
                self.lyr1=lyr
                msg=self.mesaj_yap("İşleme Giren",lyr.featureCount())
                self.mesaj+=msg
                #Birleştirme öncesi şekil yapma/ Bu aşamada kongen yapılmaz
                if self.params["sekil"]:
                    lyr1=sekilYap2(lyr,tolR=self.params["TolDo"],\
                        tolC=self.params["TolDa"],dr=self.params["minK"],\
                        da=self.params["da1"],daci=self.params["daci"],
                        daln=self.params["da3"],dknr=self.params["dknr"],kongen=False)
                    self.bilgi.setText("Şekil yap bitti!")
                else:
                    lyr1=lyr
                msg=self.mesaj_yap("Birl. Ö.",lyr1.featureCount())
                self.mesaj+=msg
                lyr2=birlestir(lyr1,bdist=self.params["dtamp"])
                self.bilgi.setText("Birleştir bitti!")
                msg=self.mesaj_yap("Birl. S.",lyr2.featureCount())
                self.mesaj+=msg
                plyr=alan_eleme(lyr2,a1=self.params["da1"],a2=self.params["da2"])
                msg=self.mesaj_yap("Alan Eleme S..",lyr2.featureCount())
                self.mesaj+=msg
                n_pnt=plyr.featureCount()
                if self.params["kongen"]:
                    lyr3=sekilYap2(lyr2,tolR=self.params["TolDo"],\
                        tolC=self.params["TolDa"],dr=self.params["minK"],\
                        da=self.params["da1"],daci=self.params["daci"],
                        daln=self.params["da3"],dknr=self.params["dknr"],kongen=True)
                    lyr3.setName(lyr2.name())
                    QgsProject.instance().addMapLayer(lyr3)
                    n_poli=lyr3.featureCount()
                    self.bilgi.setText("Kongen bitti!")
                else:
                    QgsProject.instance().addMapLayer(lyr2)
                    n_poli=lyr2.featureCount()
                if n_pnt>0:
                    QgsProject.instance().addMapLayer(plyr)
        self.bilgi.setText("İşlem Tamam!")
        self.katman_al()
        # self.buttonBox.setEnabled(False)
        dt=time.time()-self.t0
        msg=self.mesaj_yap("Bitti! Süre",dt)
        self.mesaj+=msg
        msg=self.mesaj_yap("Çokgen S.",n_poli)
        self.mesaj+=msg
        msg=self.mesaj_yap("Nokta S.",n_pnt)
        self.mesaj+=msg
        self.textMsg.setPlainText(self.mesaj)
        self.kopyala()

        
