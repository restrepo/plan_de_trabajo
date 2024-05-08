from IPython.display import JSON

# The browser must have headless  = False to pass capthca
import helium as hell
from selenium.webdriver.common.by import By
import pandas as pd
import io
from time import sleep
from getpass import getpass
from re import search
from copy import deepcopy
import json
from unidecode import unidecode
from cryptography.fernet import Fernet
from os.path import isfile
from IPython.display import display
from ipywidgets import widgets

def radio(description,options=[True, False]):
    w = widgets.RadioButtons(
        options=options,
    #    layout={'width': 'max-content'}, # If the items' names are long
        description=description,
        disabled=False
    )
    if False in options:
        w.value = False # Defaults to 'pineapple'
    return w

def drop(description,options):
    value = options[0]
    return widgets.Dropdown(
        options=options,
        value=value,
        description=description,
        disabled=False,
    )

def get_config(defaults=[]):
    radios = {}
    drops = {}
    ii = 0
    for k in ['Salvar la base de datos', 
              'Actualizar la base de datos', 
              'Enviar el plan de trabajo al profesor',
              'Autenticarse de nuevo', 'RESET i: ignorando la base de datos'
             ]:
        radios[k] = radio(k)
        if k == 'Actualizar la base de datos' or k == 'Salvar la base de datos':
            radios[k].value = True
        if defaults:
            radios[k].value = defaults[ii]
        
        display(radios[k])
        ii += 1

    drops['Grupo de profesores'] = drop('Profesores',['Instituto','Todos'])
        
    drops['Estado del plan de trabajo'] = drop('Estado',['Autorizado','Aprobado','Diligenciado','Devuelto para revisión'])
    
    semesters = []
    this_year = int(get_semester().split('-')[0])
    this_semester = int(get_semester().split('-')[-1])
    for y in range(2017,this_year+1)[::-1]:
        for semester in [2,1]:
            if y == this_year and semester > this_semester:
                continue
            semesters.append(f'{y}-{semester}')

    drops['Semestre'] = drop('Semestre',semesters)  
        
    print('─' * 80)
    for k in ['Grupo de profesores','Estado del plan de trabajo','Semestre']:
        if defaults:
            drops[k].value = defaults[ii]
    
        display(drops[k])
        ii += 1

    
    return radios,drops



def loop(i,lptd,ptd,
         SAVE_DATABASE = False,
         ENVIAR = False,
         file = 'kk.json'):
#if True:
    print(f'input i {i}')
    while True:
    #if True:    
        ptd.DEVOLVER = []
        ptd.WARNINGS = []
        ptd.NEXT_STEP = True
        
        i = ptd.get_docente(i_docente=i,L=lptd) #CONTINUE(i_docente) inside
        if ptd.CONTINUE:
            print(f'CONTINUE {i}')
            continue

        print('wait 3 seconds...')
        sleep(3)
    
        for iii in range(10):
            ptd.get_horas_reportadas()
            if ptd.h_total == '0':
                print('wait 120 seconds...')
                sleep(120)
            sleep(3)
            if ptd.resumen_horas:
                break

        if hell.Text('CONTINUAR').exists():
            hell.click('CONTINUAR')

        if ptd.resumen_horas:
            print(f'inside tables...')
            #Addtional check here
            ptd.get_docencia()

            if hell.Text('CONTINUAR').exists():
                hell.click('CONTINUAR')
            
            
            ptd.get_investigación()

            if hell.Text('CONTINUAR').exists():
                hell.click('CONTINUAR')
            
            ptd.get_extension()

            if hell.Text('CONTINUAR').exists():
                hell.click('CONTINUAR')            
            
            ptd.get_admininstración()

            if hell.Text('CONTINUAR').exists():
                hell.click('CONTINUAR')
            
            ptd.get_otras()

            if hell.Text('CONTINUAR').exists():
                hell.click('CONTINUAR')
                    
        else:
            i = CONTINUE(i)
    
        DEVOLVER = ptd.append_DEVOLVER() # Data scheme used here!
    
        # TODO → Move to self.method(lptd)
        msg_autorizar = ptd.get_mensaje_autorizar() #Required by ptd.to_dict()
        if ENVIAR and ptd.DEVOLVER:
            msg = '\n'.join(ptd.DEVOLVER)
            hell.click('Devolver')
            hell.write(msg, into = 'MOTIVO')
            hell.click('Aceptar')
            hell.wait_until( hell.Text('El plan ha sido actualizado exitosámente y ha quedado en estado Devuelto para revisión.').exists,timeout_secs=ptd.timeout )
            sleep(3)
            hell.click('Aceptar')
            print('Devuelto\n','\n'.join(ptd.DEVOLVER))
            i = CONTINUE(i)
    
        # TODO → Move to self.method(lptd)
        elif ENVIAR:
            hell.click('Autorizar')
            hell.write(msg_autorizar, into = 'Observaciones')
            hell.click('Aceptar')
            hell.wait_until( hell.Text('El plan ha sido actualizado exitosámente y ha quedado en estado Autorizado.').exists,timeout_secs=120 )
            sleep(3)
            hell.click('Aceptar')
            print('Autorizar\n',msg_autorizar)
            #input('Desapareció pup up? (Hit <Enter>)')
            lptd = ptd.add_to_list(lptd)
            #lptd.append( deepcopy(ptd.to_dict()) )
        else:            
            lptd = ptd.add_to_list(lptd)
            #lptd.append( deepcopy(ptd.to_dict()) )
        
        print(f'aprobados: {len(lptd)}')
    
        # TODO → Move to self.method(lptd)
        if SAVE_DATABASE:
            f=open(file,'w')
            json.dump(lptd,f)
            f.close()
            
        print('Next docente...')
        #raise Exception('C')
        i = CONTINUE(i)
    return i, lptd, ptd

def find_element(x,by,value):
    try:
        return x.find_element(by,value)
    except:
        return None

def fix_column(table,df,column):
    s = df[column]
    for s_i in range(len(s)):
        t = df.loc[s_i,column]
        if search(r'\.\.\.$',t):
            long_t = [xx.get_property('title') for xx in table.find_elements(By.TAG_NAME,'td') if xx.text == t ]
            if long_t:
                df.loc[s_i,column] = long_t[0]
    return df

def get_compromisos(entregables,df):
    return list( entregables.intersection( ' '.join(((df.Actividad + df.Descripción
             ).apply(unidecode).to_list())).split()) )

def CONTINUE(i):
    #hell.get_driver().back()
    print('wait 2 seconds...')
    sleep(2)
    hell.wait_until( hell.Text("Volver").exists,timeout_secs=120 )
    hell.click("Volver")
    hell.wait_until( hell.Text('Fecha inicio semestre').exists,timeout_secs=240 )
    return i+1

def  get_semester():
    from datetime import datetime
    semester = 1
    if datetime.now().month > 6:
        semester =2
    return f'{datetime.now().year}-{semester}'

def login():
    hell.go_to("https://www.udea.edu.co/wps/portal/udea/web/inicio/login")

    login_file = 'login.enc'
    if not isfile(login_file):
        usuario = input('usuario')
        contraseña = getpass('contraseña')    
        ## key generation → Cannot be in repo!!!
        key = Fernet.generate_key()
     
        ## string the key in a file
        with open('filekey.key', 'wb') as filekey:
           filekey.write(key) 
        
        # opening the key
        with open('filekey.key', 'rb') as filekey:
            key = filekey.read()
         
         
        # using the generated key
        fernet = Fernet(key)
        
        encrypted = fernet.encrypt(f'{{"usuario": "{usuario}", "contraseña": "{contraseña}"}}'.encode('utf8'))
         
        # opening the file in write mode and 
        # writing the encrypted data
        with open(login_file, 'wb') as encrypted_file:
            encrypted_file.write(encrypted)
        print('local encrypted login file have been created')
    else:
        print(f'Using existing local encrypted login file from previos run: ./{login_file}')
    
    with open('filekey.key', 'rb') as filekey:
        key = filekey.read()
         
    # using the generated key
    fernet = Fernet(key)
    
    
    with open(login_file, 'rb') as enc_file:
        encrypted = enc_file.read()
     
    # decrypting the file
    decrypted = fernet.decrypt(encrypted)
    
    login = eval(decrypted.decode('utf8'))
    # internal variables inside function
    usuario = login['usuario']
    contraseña = login['contraseña']

    hell.write(usuario,into='*Usuario')
    hell.write(contraseña,into='*Contraseña')
    
    hell.click("I'm not a robot")
    print('wait fo 2 seconds')
    sleep(2)
    try:
        # https://gist.github.com/Ramhm/9cc4976c05bee176871c46d28710aebe
        kk = hell.get_driver().find_element(By.XPATH,'//span[@aria-checked="true"]')
    except:
        input('Captcha solved? (Hit <Enter>')
    sleep(1)
    hell.click('Conectar')
    
#hell is global
class PTD:
    '''
    Caracterśiticas:
    * Número de horas diligenciadas
    * Cursos con 0 horas
    * Código SIU de proyectos
    * Actividades de apoyo a la gestión académica-administrativa con 45 horas
    * Comprueba si hay compromisos y pide entregables a través de un formulario
      a través de un formulario de Google durante el mes siguiente la finalización
      del semestre
    '''
    #Global variables
    timeout = 180 #secs
    SINGLE = False
    compromisos = []
    estado = "Diligenciado"
    todos = False
    this_semestre = get_semester()
    semestre = "2024-1"    
    n_page = 20
    n_total = 10000
    def __init__(self,url="https://ayudame2.udea.edu.co/php_app/?app=inicio&appid=PLANDOCEN",i_page=1,go_to_url=True): #with previous commands
        self.i_page = i_page
        self.DEVOLVER = []
        self.WARNINGS = []
        self.NEXT_STEP = True

        if go_to_url:
            hell.go_to(url)
    
            hell.wait_until( hell.Text('Gestionar planes').exists, timeout_secs=self.timeout)
            
            if not hell.Text('Gestionar planes').exists():
                self.NEXT_STEP = False

    def gestionar_planes(self,institutos = ['BIOLOGIA','FISICA','MATEMATICA','QUIMICA', 'CIENCIAS DEL MAR'],SINGLE = False, cedula = None):
        """
        Make the search
        """
        self.SINGLE = SINGLE
        hell.click('Gestionar planes')

        print('wait 10 seconds...') #slew page some times
        sleep(10)
        
        
        hell.wait_until( hell.Text("Búsqueda avanzada").exists,timeout_secs=self.timeout )
        
        print('wait 5 seconds...')
        sleep(5)
        hell.click('Búsqueda avanzada')
        print('wait 2 seconds...')
        sleep(2)

        hell.wait_until( hell.TextField("Facultad Ciencias Exactas y Naturales").exists,timeout_secs=self.timeout )
        
        for I in institutos:
            x = f"INSTITUTO DE {I}"
            instituto = None
            if hell.TextField(x).exists():
                instituto = x
                break
        
        if not instituto:
            print('ERROR: Insituto no encontrado')
            #break
        
        sleep(1)

        if not self.semestre:
            self.semestre = self.this_semestre
            
        if self.this_semestre != self.semestre:
            hell.select(self.this_semestre,self.semestre)
        
        hell.click( hell.RadioButton("Planes diligenciados") )
        
        if not self.todos:
            hell.select("Todos",instituto)
        
        hell.select("Todas",self.estado)
        
        if self.SINGLE:
            hell.write('313558','Identificación del docente') 
        
        hell.click('Buscar')

        #TODO: Get total records from page
        try:
            #hell.wait_until(hell.Text('xxx').exists,timeout_secs = self.timeout)
            self.n_total = 72
        except:
            self.n_notal = 1000

    def go_to_initial_page(self):
        if self.i_page > 1:
            for p in range(2,self.i_page+1):
                hell.click("Siguiente")
                print(f'wait 2 seconds... {p}')
                sleep(2)
                hell.wait_until( hell.Text('Fecha inicio semestre').exists,timeout_secs=240 )
        
    def get_docente(self,i_docente=0,L=[]):
        print(f'page: {self.i_page}; i: {i_docente} ')
        try:
            #**************  GET docente info → TODO: move to a function *******
            hell.wait_until( hell.Text('Fecha inicio semestre').exists,timeout_secs=240 )
            ALL = hell.get_driver()
            tables = ALL.find_elements(By.CLASS_NAME, 'table-responsive')
            x = tables[i_docente] # Si no hay más docentes en página ésta linea genera Error
            #******************************************************************
            if self.i_page == 1:
                self.n_page = len(tables) # The same for all pages. Fix the Default value
        except:
            if not ALL.find_elements(By.TAG_NAME, "li")[0].get_attribute('innerHTML').find("pagination-next ng-scope disabled") > -1:
                self.i_page += 1
                i_docente = 0
                print(f"page: {self.i_page}")
                hell.click("Siguiente")
                #**************  GET docente info → TODO: move to a function *******
                hell.wait_until( hell.Text('Fecha inicio semestre').exists,timeout_secs=240 )
                ALL = hell.get_driver()
                tables = ALL.find_elements(By.CLASS_NAME, 'table-responsive')
                x = tables[i_docente] # Si no hay más docentes en página ésta linea genera Error
                #******************************************************************                            
            else:
                raise Exception("Saliendo: Todos los docentes encontrados")            
            
        
        self.diligenciado = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        print(f'Docente: {self.diligenciado.Docente.iloc[0]}')
        self.CONTINUE = False
        if self.diligenciado.Docente.iloc[0].split(' - ')[0] in [
            d['información_general']['identificación'] for d in L]:
            print('Already in database')
            i_docente += 1 
            self.CONTINUE = True
            return i_docente
    
        # Va al primer docente
        print('wait 5 seconds...')
        sleep(5)
    
        if self.SINGLE:
            hell.wait_until( hell.Text('Docente').exists )
            L = [x for x in driver.find_elements(By.TAG_NAME,'a') if x.get_attribute('class') == 'btn btn-xs ng-scope']
            if len(L) == 4:
                L[2].click()
        #else:
        
        las = ALL.find_elements(By.TAG_NAME, 'a')
        
        docentes = [ x for x in  ALL.find_elements(By.TAG_NAME, 'a') if find_element(x,By.TAG_NAME,'img') and x.find_element(By.TAG_NAME,'img').get_attribute('title')== 'Ver plan']

        
        docentes[i_docente].click()

        # TODO: Change for a hell.wait_until with time
        print('wait 1+10 seconds...')
        sleep(1)

        try:
            hell.wait_until(hell.Text('Resumen de cambios').exists, timeout_secs=10 )
        except:
            pass

        if hell.Text('Resumen de cambios').exists():
            hell.click('Aceptar')
        
        hell.wait_until(hell.Text('Horas diligenciadas').exists, timeout_secs=self.timeout )

        return i_docente

    def get_horas_reportadas(self):
        print('wait 2 seconds...')
        sleep(2)
        
        hell.click('Información general')
        hell.wait_until( hell.Text('Topes de horas a diligenciar').exists,timeout_secs=self.timeout )
        
        print('wait 5 seconds...')
        sleep(5)

        ptdh = hell.get_driver()
        
        self.h_total = ptdh.find_element(By.CLASS_NAME,'contador-horas-completadas').text.split('\n')[0]
        
        self.msg_h_acompletar = ptdh.find_element(By.CLASS_NAME,'horas-acompletar-titulo').text
        x = self.msg_h_acompletar.split()
        
        if len(x) == 5: #TODO 
            horas_acompletar = x[-2]
        else:
            horas_acompletar = '0'
        print("h_total != horas_acompletar",self.h_total,horas_acompletar)
        # TODO: add to table to analyze with append_DEVOLVER()
        #if h_total != '0' and h_total != horas_acompletar:
        #    self.DEVOLVER.append(f'Horas reportadas: {h_acompletar}')
        h_reportadas = ptdh.find_element(By.CLASS_NAME,'background-cards-resumen-horasreportadas')
        
        h_reportadas = h_reportadas.find_element(By.TAG_NAME,'tbody').find_elements(By.TAG_NAME,'tr')

        self.h_reportadas = h_reportadas #DEBUG → Convert to pandas directly
        len(h_reportadas) == 5 #TODO
        
        #def convert vertical table to dict
        self.resumen_horas = {}
        for i in range(len(h_reportadas)):
            k = h_reportadas[i].find_elements(By.TAG_NAME,'td')[0].text
            self.resumen_horas[k] = h_reportadas[i].find_elements(By.TAG_NAME,'td')[-1].text

        if self.resumen_horas: #Already filter that h_total != '0'
            self.resumen_horas['h_total'] = self.h_total
            self.resumen_horas['horas_acompletar'] = horas_acompletar
            self.resumen_horas = dict( zip(self.resumen_horas.keys(),
                  [int(x) for x in self.resumen_horas.values()] ) )                

        print('wait 2 seconds...')
        sleep(2)
        

    def get_docencia(self):
        hell.click('Docencia')
        
        hell.wait_until(hell.Text('Actividades de docencia').exists, timeout_secs=self.timeout)
        
        print('wait 2 seconds...')
        sleep(2)
        
        docencia = hell.get_driver()
        
        tables = docencia.find_elements(By.CLASS_NAME, 'table-responsive')
        x = tables[0]
        
        self.Actividades_de_docencia = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        #Actividades_de_docencia
        
        presencial = 5
        if self.Actividades_de_docencia['Número de alumnos'].max() <= 5:
            self.WARNINGS.append('Actividades de Docencia: Debe tener al menos un curso presencial a su cargo')
            
        x = tables[1]
        
        self.Actividades_relacionadas_con_la_docencia = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        
        #self.Actividades_relacionadas_con_la_docencia = fix_column(tables[0],self.Actividades_relacionadas_con_la_docencia,'Actividad')
        self.Actividades_relacionadas_con_la_docencia = fix_column(x,self.Actividades_relacionadas_con_la_docencia,'Descripción')

        
    def get_investigación(self):
        
        hell.click('Investigación')
        
        hell.wait_until(hell.Text('Actividades de investigación').exists, timeout_secs=self.timeout)
        
        print('wait 2 seconds...')
        sleep(2)

        investigación = hell.get_driver()
        
        tables = investigación.find_elements(By.CLASS_NAME, 'table-responsive')
        x = tables[0]
        
        self.Actividades_de_investigación = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        #Actividades_de_investigación
        
        self.Actividades_de_investigación = fix_column(x,self.Actividades_de_investigación,'Actividad')
        
        x = tables[1]
        self.Actividades_relacionadas_con_la_investigación = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        
        #self.Actividades_relacionadas_con_la_investigación = fix_column(tables[0],self.Actividades_relacionadas_con_la_investigación,'Actividad')
        self.Actividades_relacionadas_con_la_investigación = fix_column(x,self.Actividades_relacionadas_con_la_investigación,'Descripción')
        
    def get_extension(self):
        hell.click('Extensión')
        
        hell.wait_until( hell.Text('Actividades de extensión').exists, timeout_secs=self.timeout )
        
        print('wait 2 seconds...')
        sleep(2)
        
        
        extensión = hell.get_driver()
        tables = extensión.find_elements(By.CLASS_NAME, 'table-responsive')
        x = tables[0]
        self.Actividades_de_extensión = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        #Actividades_de_extensión
        
        x = tables[1]
        self.Actividades_relacionadas_con_la_extensión = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        
        self.Actividades_relacionadas_con_la_extensión = fix_column(x,self.Actividades_relacionadas_con_la_extensión,'Descripción')
        
        
    def get_admininstración(self):
        hell.click('Administración académica')
        
        hell.wait_until( hell.Text('Actividades de administración').exists, timeout_secs=self.timeout )
        
        print('wait 2 seconds...')
        sleep(2)
        
        
        administración = hell.get_driver()
        tables = administración.find_elements(By.CLASS_NAME, 'table-responsive')
        x = tables[0]
        self.Actividades_de_administración = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        
        self.Actividades_de_administración = fix_column(x,self.Actividades_de_administración,'Descripción')
        
    def get_otras(self):
        hell.click('Otras')
        
        hell.wait_until( hell.Text('Otras Actividades').exists, timeout_secs=self.timeout )
        
        print('wait 2 seconds...')
        sleep(2)
        
        
        otras = hell.get_driver()
        tables = otras.find_elements(By.CLASS_NAME, 'table-responsive')
        x = tables[0]
        self.Otras_Actividades = pd.read_html( io.StringIO( x.get_attribute('innerHTML') ) )[0]
        
        self.Otras_Actividades = fix_column(x,self.Otras_Actividades,'Descripción')

    def to_dict(self):
        # TODO: Replace NaN for None
        #Prepare JSON output
        ptdi = {}
        ptdi['información_general'] = self.diligenciado.to_dict(orient='records')[0]
        ptdi['información_general']['identificación'] = ptdi['información_general'].get('Docente').split(' - ')[0]
        ptdi['información_general']['Docente'] = ptdi['información_general'].get('Docente').split(' - ')[-1]
        
        ptdi['resumen_horas'] = self.resumen_horas
        
        ptdi['actividades_de_docencia'] = self.Actividades_de_docencia.to_dict(orient='records')
        ptdi['actividades_relacionadas_con_la_docencia'] = self.Actividades_relacionadas_con_la_docencia.to_dict(orient='records')
        
        ptdi['actividades_de_investigación'] = self.Actividades_de_investigación.to_dict(orient='records')
        ptdi['actividades_relacionadas_con_la_investigación'] = self.Actividades_relacionadas_con_la_investigación.to_dict(orient='records')
        
        ptdi['actividades_de_extensión'] = self.Actividades_de_extensión.to_dict(orient='records')
        ptdi['actividades_relacionadas_con_la_extensión'] = self.Actividades_relacionadas_con_la_extensión.to_dict(orient='records')
        
        ptdi['actividades_de_administración'] = self.Actividades_de_administración.to_dict(orient='records')
        
        ptdi['otras_Actividades'] = self.Otras_Actividades.to_dict(orient='records')

        ptdi['WARNINGS'] = self.WARNINGS
        ptdi['compromisos'] = self.compromisos
        ptdi['DEVOLVER'] = self.DEVOLVER
        return ptdi

    def get_actividades(self,L=[]):
        actividades = {}
        actividades_relacionadas = ['actividades_relacionadas_con_la_docencia',
                            'actividades_relacionadas_con_la_investigación',
                            'actividades_relacionadas_con_la_extensión',
                            'otras_Actividades']
        if L:
            lptd = L
        else:
            ltpd = self.to_dict()
        pd.set_option('display.max_rows', 500)            
        pd.set_option('display.max_colwidth',200)
        for k  in actividades_relacionadas:
            actividades[k] = pd.DataFrame()
            for s in lptd:
                lari = s[k]
                if lari:
                    tmp = pd.DataFrame( lari )
                    tmp['identificación'] = s['información_general']['identificación']
                    actividades[k] = pd.concat((actividades[k], tmp))
            
            actividades[k] = actividades[k].reset_index(drop=True)
            self.actividades = actividades

    def get_mensaje_autorizar(self):
        msg = '\n'.join(self.WARNINGS)
    
        entregables = ['material de docencia','capacitación','manuscrito', 'artículo']
        entregables = set( [ unidecode(x) for x in entregables ] )
        
        compromisos = []
        
        compromisos = compromisos + get_compromisos(entregables,self.Actividades_relacionadas_con_la_docencia)
        compromisos = compromisos + get_compromisos(entregables,self.Actividades_relacionadas_con_la_investigación)
        compromisos = compromisos + get_compromisos(entregables,self.Actividades_relacionadas_con_la_extensión)
        compromisos = compromisos + get_compromisos(entregables,self.Otras_Actividades)

        # Desplegables Plan de Trabajo
        entregables2 = ['Producción de material de docencia',
                        'Diseño y preparación de cursos nuevos',
                        'Preparación de productos derivados de investigación',
                        'Preparación de proyectos de investigación',
                        'Ponencias derivadas de investigación en congresos o seminarios',
                        'Preparación de proyectos de extensión',
                        'Preparación de conferencias y/o eventos'
                        'Cursos de capacitación y/o actualización autorizados']

        compromisos2 = any( [ not self.Actividades_relacionadas_con_la_docencia[
                              self.Actividades_relacionadas_con_la_docencia['Actividad'
                             ].apply(lambda a: a in entregables2)].empty,
                              not self.Actividades_relacionadas_con_la_investigación[
                              self.Actividades_relacionadas_con_la_investigación['Actividad'
                             ].apply(lambda a: a in entregables2)].empty,
                              not self.Actividades_relacionadas_con_la_extensión[
                              self.Actividades_relacionadas_con_la_extensión['Actividad'
                             ].apply(lambda a: a in entregables2)].empty,
                              not self.Otras_Actividades[
                              self.Otras_Actividades['Actividad'
                             ].apply(lambda a: a in entregables2)].empty]
                           )

        self.compromisos = compromisos
        conector = ''
        if compromisos or compromisos2:
            if msg:
                conector='\n'
            msg  = msg+conector+'Subir entregables de compromisos al formulario: https://forms.gle/MKDwMRuvTmVwhADV8, durante el mes siguiente a la terminación del semestre'
        return msg

    def append_DEVOLVER(self):
        '''
        El esquema de datos debe permitir todos los análisis
        '''
        DEVOLVER = False
        if self.resumen_horas['h_total'] and self.resumen_horas['h_total'] != self.resumen_horas['horas_acompletar']:
            self.DEVOLVER.append(f'Horas reportadas: {self.msg_h_acompletar}')
        
        qs=['horas', 'alumnos']
        for q in qs:
            if self.Actividades_de_docencia[self.Actividades_de_docencia[f'Número de {q}']==0]['Horas planeadas'].sum()>0:
                self.DEVOLVER.append(f'Actividades de Docencia: "Horas planeadas" para cursos con 0 {q} mayores a 0')

        L = self.Actividades_de_investigación['Código'].to_list()
        if not self.Actividades_de_investigación.empty and not L:
            self.DEVOLVER.append('"Actividades de investigación": Los proyectos deben tener código SIU. Mover a "Actividades relacionadas con la investigación" con compromiso explícito')

        reuniones = self.Otras_Actividades[self.Otras_Actividades['Actividad'] == 'Actividades de apoyo a la gestión académica-administrativa']
        if reuniones.empty:
            reuniones = self.Otras_Actividades[self.Otras_Actividades['Actividad'].str.lower().str.contains('reuniones')]
        if reuniones.empty:
            reuniones = self.Otras_Actividades[self.Otras_Actividades['Actividad'].str.lower().str.contains('claustro')]
        if not reuniones.empty and reuniones['Horas planeadas'].iloc[0] >= 45:
            pass
        else:
            self.DEVOLVER.append('Otras actividades: Es oblogatorio incluir "Actividades de apoyo a la gestión académica-administrativa", que incluyen las reuniones, con 45 horas')

        atención = self.Actividades_relacionadas_con_la_docencia[self.Actividades_relacionadas_con_la_docencia['Actividad'] == 'Atención a estudiantes']
        if atención.empty:
            self.DEVOLVER.append('Actividades relacionadas con la docencia: Es oblogatorio incluir horas en "Atención a estudiantes"')        
            
        if self.DEVOLVER:
            DEVOLVER = True
        return DEVOLVER

    def get_docentes_by_identificación(self,L):
        self.docentes = dict( [(d['información_general']['identificación'], d['información_general']['Docente']) for d in L])
        return self.docentes

    def add_to_list(self,L):
        """
        TODO: Don't use until final design is decided. Currently: Run all again!
        """
        D = self.to_dict()
        
        if not [d['información_general']['identificación'] for d in L 
            if d['información_general']['identificación'] == D['información_general']['identificación']]:
            L.append( deepcopy(D) )
        return L # already there
        
    def get_max_indices(self):
        self.check_max_index = {1: (0,1), 10: (9,1), 19: (18,1), 
                                20: (19,1),21: (0,2),30: (9,2),
                                40: (19,2),41: (0,3)}
        i_total = self.n_total -1
        i_page_max = int(i_total/self.n_page) + 1
        i_max = i_total - (i_page_max - 1)*self.n_page
        # assert self.get_max_indices(41) == self.check_max_index[41]
        return i_max, i_page_max        