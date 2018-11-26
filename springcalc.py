#!/usr/bin/env python
"""Superior Moldie, C.A.
   San Diego 2006, Venezuela
   by Alberto Vázquez
   v1.0.1"""
from spring import Spring, eSpring, tSpring
from tkinter import Tk, Frame, Button, Label, \
     Entry, LabelFrame, Text, Radiobutton, DoubleVar, StringVar, messagebox
from tkinter.ttk import Notebook, Combobox
from collections import OrderedDict
from time import strftime
import sys
import os
import traceback
import multiprocessing

"""
Recipe for using multiprocessing in windows' exe, created by pyinstaller:
https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing
"""
try:
    # Python 3.4+
    if sys.platform.startswith('win'):
        import multiprocessing.popen_spawn_win32 as forking
    else:
        import multiprocessing.popen_fork as forking
except ImportError:
    import multiprocessing.forking as forking

if sys.platform.startswith('win'):
    # First define a modified version of Popen.
    class _Popen(forking.Popen):
        def __init__(self, *args, **kw):
            if hasattr(sys, 'frozen'):
                # We have to set original _MEIPASS2 value from sys._MEIPASS
                # to get --onefile mode working.
                os.putenv('_MEIPASS2', sys._MEIPASS)
            try:
                super(_Popen, self).__init__(*args, **kw)
            finally:
                if hasattr(sys, 'frozen'):
                    # On some platforms (e.g. AIX) 'os.unsetenv()' is not
                    # available. In those cases we cannot delete the variable
                    # but only set it to the empty string. The bootloader
                    # can handle this case.
                    if hasattr(os, 'unsetenv'):
                        os.unsetenv('_MEIPASS2')
                    else:
                        os.putenv('_MEIPASS2', '')

    # Second override 'Popen' class with our modified version.
    forking.Popen = _Popen

def resource_path(relative):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative)

def except_handler(ex):
    print("La solución superó su tiempo máximo establecido. Error de tipo {}: "
          "{}".format(type(ex).__name__, ex))

class StdoutRedirector(object):
    """Class to redirect stdout and traceback to a text widget"""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        if not "\n" in string:
           string = "(" + strftime("%I:%M:%S %p") + ") " + string
        self.text_widget.insert('end', string)
        self.text_widget.see('end')

    def flush(self):
        sys.__stdout__.flush()



class cFrame(Frame):
    """Basic structure for frames inside the notebook's tabs"""
    def __init__(self, parent, pos, name, spring=None):
        self.parent = parent
        self.spring = spring
        super().__init__(parent)
        self.frame = LabelFrame(self.parent, text=name)
        self.frame.grid(column=pos[0], row=pos[1], columnspan=pos[2],
                        sticky='nsew', padx=5, pady=5)
        for i in range(pos[2]):
            self.frame.grid_columnconfigure(i, weight=1)
        self.parent.bind('<<solved>>', self.enaButtons, add='+')
        self.parent.bind('<<unsolved>>', self.disButtons, add='+')
        self.entries = OrderedDict()

    def createButtons(self, tup1, tup2):
        rstButton = Button(self.frame, text='Borrar', command=self.rst)
        rstButton.grid(row=tup1[1], column=tup1[0], columnspan=tup1[2],
                       sticky='w', padx=5, pady=4)
        solveButton = Button(self.frame, text='Resolver',
                             command=self.solve)
        solveButton.grid(row=tup2[1], column=tup2[0], columnspan=tup2[2],
                         sticky='e', padx=5, pady=4)

    def cleanEntries(self):
        for k in self.entries.keys():
            self.entries[k]['entry'].configure(bg='white')
            self.entries[k]['entry'].delete(0, 'end')

    def enaButtons(self, event):
        for k in self.entries.keys():
            self.entries[k]['entry']['state'] = 'normal'

    def disButtons(self, event):
        for k in self.entries.keys():
            self.entries[k]['entry']['state'] = 'disabled'


class subWindow(Frame):
    def __init__(self, parent, spring):
        self.parent = parent
        super().__init__(parent)
        self.spring = spring
        self.lf1 = lFrame1(self.parent, (0, 0, 2), "Parámetros de resorte",
                           self.spring)
        self.lf2 = lFrame2(self.parent, (0, 1, 1), "Cálculo estático",
                           self.spring)
        self.lf3 = lFrame3(self.parent, (1, 1, 1), "Cálculo dinámico",
                           self.spring)

    def init_widgets(self):
        self.lf1.init_widget()
        self.lf2.init_widget()
        self.lf3.init_widget()


class lFrame1(cFrame):
    def __init__(self, parent, pos, name, spring):
        super().__init__(parent, pos, name, spring)
        cbMat = {}
        cbFix = {}
        cbEnd = {}
        self._wlabel = StringVar()
        matList = self.spring._getData("SELECT NAME, MATERIAL FROM MATERIALS",
                                       ())
        for i in range(0, len(matList)-1, 2):
            cbMat[matList[i]] = matList[i+1]
        endList = ('Cerrado y esmerilado', 'Cerrado', 'Abierto y esmerilado',
                   'Abierto')
        for (k, v) in zip(endList, self.spring._endList):
            cbEnd[k] = v
        fixList = ('Ambos extremos fijos y placas paralelas',
                   'Un extremo fijo y otro pivotea',
                   'Ambos extremos pivotean',
                   'Un extremo amarrado y otro libre')
        for (k, v) in zip(fixList, self.spring._fixList):
            cbFix[k] = v
        matDict = {'text': 'Material:', 'values': cbMat, 'entry': None}
        endDict = {'text': 'Terminación:', 'values': cbEnd, 'entry': None}
        fixDict = {'text': 'Fijación:', 'values': cbFix, 'entry': None}
        self.cbEntries = OrderedDict([('material', matDict),
                                      ('ending', endDict),
                                      ('fixing', fixDict)])
        names = ['d', 'DE', 'DM', 'DI', 'Nt', 'Na', 'Lo', 'Ls', 'p',
                       'gap', 'w', 'C', 'k']
        texts = ['Calibre:', 'Diam. Ext.:', 'Diam. Med.:', 'Diam. Int.:',
                 'Vueltas totales:', 'Vueltas activas:',
                 'Longitud libre:', 'Longitud sólida:', 'Paso:',
                 'Paso Luz:', 'Peso:', 'Radio Dm/d:', 'Constante:']
        units = ['mm', 'mm', 'mm', 'mm', '', '', 'mm', 'mm', 'mm', 'mm',
                 'Kg', 'mm/mm', 'N/mm']
        for (n, t, u) in zip(names, texts, units):
            self.entries[n] = {'text': t, 'unit': u, 'entry': None,
                               'entryVar': StringVar()}

    def init_widget(self):
        i = 0
        for k in self.cbEntries.keys():
            l = Label(self.frame, text=self.cbEntries[k]['text'])
            l.grid(column=0, row=i, sticky='w')
            e = Combobox(self.frame, width=30)
            e['values'] = sorted(self.cbEntries[k]['values'].keys())
            e.grid(column=1, row=i, columnspan=6, sticky='w', padx=10, pady=2)
            self.cbEntries[k]['entry'] = e
            if k == 'ending':
                e.current(3)
            else:
                e.current(0)
            i += 1
        (i, j) = self.createEntries(i)
        butPos = i // 2 if i % 2 == 0 else i // 2 + 1
        self.createButtons((butPos, j, 2), (butPos-2, j, 2))

    def checkInput(self, *args):
        for k in self.entries.keys():
            if args[0].__str__() == self.entries[k]['entryVar'].__str__():
                modKey = k
                aux = self.entries[modKey]['entryVar'].get()
        try:
            v = float(aux)
        except:
            if len(aux) > 0:
                self.entries[modKey]['entry'].configure(bg="#d73c37")
            else:
                self.entries[modKey]['entry'].configure(bg="white")
        else:
            self.entries[modKey]['entry'].configure(bg="white")

    def createEntries(self, first):
        i = first
        j = 0
        labelPerCol = 4 + first
        for k in self.entries.keys():
            if i >= labelPerCol:
                i = first
                j += 3
            l = Label(self.frame, text=self.entries[k]['text'])
            l.grid(column=j, row=i, sticky='w', pady=2)
            if k == 'w':
                lu = Label(self.frame, textvariable=self._wlabel,
                           text=self.entries[k]['unit'])
                self._wlabel.set(self.entries[k]['unit'])
            else:
                lu = Label(self.frame, text=self.entries[k]['unit'])
            lu.grid(column=j+2, row=i, sticky='w', pady=2, padx=(0, 10))
            e = Entry(self.frame, width=8, textvariable=self.
                      entries[k]['entryVar'])
            self.entries[k]['entryVar'].trace('w', self.checkInput)
            e.grid(column=j+1, row=i, sticky='e', padx=0, pady=2)
            self.entries[k]['entry'] = e
            i += 1
        j += 3
        return (j, labelPerCol)

    def writeResult(self):
        for (k, v) in self.spring.__dict__.items():
            if k in self.entries.keys():
                if k == 'w' and v <= 0.1:
                    v = v * 1000
                    self._wlabel.set('g')
                elif k == 'w' and v > 0.1:
                    self._wlabel.set('Kg')

                if k == 'k':
                    self.entries[k]['entry'].insert(0, "{0:.3e}".format(v))
                else:
                    self.entries[k]['entry'].insert(0, "{0:.3f}".format(v))

    def inputDict(self, *args):
        result = {}
        for k in self.entries.keys():
            v = self.entries[k]['entry'].get()
            try:
                v = float(v)
            except:
                self.entries[k]['entry'].configure(bg="#d73c37")
            else:
                self.entries[k]['entry'].configure(bg="white")
                result[k] = v
        return result

    def solve(self):
        if not self.spring.isSolved:
            for k in self.cbEntries.keys():
                setattr(self.spring, k,
                        self.cbEntries[k]['values']
                        [self.cbEntries[k]['entry'].get()])
            try:
                self.spring.solveParams(30, **self.inputDict())
            except Exception as ex:
                except_handler(ex)
                return
            ur = self.spring.checkUnresolved()
            if len(ur) > 0:
                print("Variables sin resolver: ", end="")
                for i in ur:
                    print("{} ".format(i), end="")
                print("")
            else:
                self.cleanEntries()
                self.writeResult()
                self.spring.verifyC()
                self.spring.verifyBuckling()
                self.parent.event_generate('<<solved>>')

    def rst(self):
        self.parent.event_generate('<<unsolved>>')
        self.cleanEntries()
        self.spring._rstParams()

    def enaButtons(self, event):
        for k in self.entries.keys():
            self.entries[k]['entry']['state'] = 'readonly'
        for k in self.cbEntries.keys():
            self.cbEntries[k]['entry']['state'] = 'disabled'

    def disButtons(self, event):
        for k in self.entries.keys():
            self.entries[k]['entry']['state'] = 'normal'
        for k in self.cbEntries.keys():
            self.cbEntries[k]['entry']['state'] = 'normal'


class lFrame2(cFrame):
    def __init__(self, parent, pos, name, spring):
        super().__init__(parent, pos, name, spring)
        self.frame.grid_columnconfigure(0, weight=0, minsize=1)
        self.frame.grid_columnconfigure(1, weight=0, minsize=1)
        self.frame.grid_columnconfigure(2, weight=0, minsize=1)
        self.frame.grid_columnconfigure(3, weight=1)
        self.frame.grid_columnconfigure(4, weight=1, minsize=1)
        self.frame.grid_columnconfigure(5, weight=1, minsize=1)
        self.result = OrderedDict()
        names = ['x', 'F', 'stress']
        texts = ['Deflexión:', 'Fueza:', 'Estrés:']
        units = ['mm', 'N', '%']
        for (n, t, u) in zip(names, texts, units):
            self.entries[n] = {'text': t, 'unit': u, 'entry': None,
                                                     'entryVar': StringVar()}
            self.result[n] = {'unit': u, 'label': None}
        self._update = False

    def init_widget(self):
        self.createEntries()

    def createEntries(self):
        i = 0
        for k in self.entries.keys():
            l = Label(self.frame, text=self.entries[k]['text'])
            l.grid(column=0, row=i, columnspan=1, sticky='w', padx=5)
            e = Entry(self.frame, textvariable=self.entries[k]['entryVar'],
                      state='disabled', width=10)
            e.grid(column=1, row=i, columnspan=1, sticky='we')
            self.entries[k]['entry'] = e
            self.entries[k]['entryVar'].trace('w', self.checkInput)
            lu = Label(self.frame, text=self.entries[k]['unit'])
            lu.grid(column=2, row=i, columnspan=1, sticky='w')
            i += 1

        i = 0
        for k in self.result.keys():
            lr = Label(self.frame, text='-')
            lr.grid(column=4, row=i, sticky='we')
            self.result[k]['label'] = lr
            lru = Label(self.frame, text=self.result[k]['unit'])
            lru.grid(column=5, row=i, sticky='w')
            i += 1
        self.msg = Label(self.frame, text='')
        self.msg.grid(column=0, row=i, columnspan=6)

    def checkInput(self, *args):
        if self._update:
            return
        for k in self.entries.keys():
            if args[0].__str__() == self.entries[k]['entryVar'].__str__():
                modKey = k
        aux = self.entries[modKey]['entryVar'].get()
        try:
            v = float(aux)
        except:
            if len(aux) > 0:
                self.entries[modKey]['entry'].configure(bg="#d73c37")
            else:
                self.entries[modKey]['entry'].configure(bg="white")
            for k in self.result.keys():
                self.result[k]['label']['text'] = '-'
                self.result[k]['label']['fg'] = 'black'
            return
        else:
            self.entries[modKey]['entry'].configure(bg="white")
            self._update = True
            for k in self.entries.keys():
                if k != modKey:
                    self.entries[k]['entry'].configure(bg="white")
                    self.entries[k]['entryVar'].set('')
            self._update = False
            self.solve(**{modKey: v})

    def solve(self, **kwargs):
        if len(kwargs) == 0:
            return
        if self.spring.isSolved:
            for (k, v) in kwargs.items():
                if k == 'stress':
                    kwargs[k] = v / 100
            doWhile = True
            while doWhile:
                if 'x' in kwargs.keys() or 'F' in kwargs.keys():
                    aux = self.spring.force(**kwargs)
                    for (k, v) in aux.items():
                        kwargs[k] = v
                if 'F' in kwargs.keys() or 'stress' in kwargs.keys():
                    aux = self.spring.stress(**kwargs)
                    for (k, v) in aux.items():
                        kwargs[k] = v
                if len(kwargs.keys()) >= 3:
                    doWhile = False
            isRed = False
            for (k, v) in kwargs.items():
                if (type(self.spring) is Spring) and k == 'stress':
                    self.result[k]['label']['text'] = "{:.2f}".\
                                                        format(float(v)*100)
                    if v > 0.4 and v <= 0.6:
                        self.result[k]['label']['fg'] = 'orange'
                        self.msg['text'] = "El resorte requiere 'set removal'"
                    elif v > 0.6:
                        self.result[k]['label']['fg'] = 'red'
                        self.msg['text'] = ("El stress es demasiado para la "
                                            "fuerza requerida")
                    else:
                        self.result[k]['label']['fg'] = 'black'
                        self.msg['text'] = ''
                elif (type(self.spring) is tSpring) and k == 'stress':
                    self.result[k]['label']['text'] = "{:.2f}".\
                                                        format(float(v)*100)
                    if ((self.spring.material == 'A227' and v > 0.8) or
                       (self.spring.material == 'T302' and v > 0.6) or
                       (v > 0.85)):
                        self.result[k]['label']['fg'] = 'red'
                        self.msg['text'] = ("El stress es demasiado para la "
                                            "fuerza requerida")
                    else:
                        self.result[k]['label']['fg'] = 'black'
                        self.msg['text'] = ''
                elif type(self.spring) is eSpring and (k == 'stress' or
                                                       k == 'stressA' or
                                                       k == 'stressB'):
                    self.result[k]['label']['text'] = "{:.2f}".\
                                                        format(float(v)*100)
                    if ((self.spring.material == 'T302' and (
                            (k == 'stress' and v > 0.35) or
                            (k == 'stressA' and v > 0.55) or
                            (k == 'stressB' and v > 0.30))) or
                        ((k == 'stress' and v > 0.45) or
                        (k == 'stressA' and v > 0.75) or
                        (k == 'stressB' and v > 0.40))):
                        self.result[k]['label']['fg'] = 'red'
                        isRed = True
                    else:
                        self.result[k]['label']['fg'] = 'black'
                    if isRed:
                        self.msg['text'] = ("El stress es demasiado para la "
                                            "fuerza requerida")
                    else:
                        self.msg['text'] = ''
                else:
                    self.result[k]['label']['text'] = "{:.2f}".format(v)


    def disButtons(self, event):
        self._update = True
        for k in self.result.keys():
            self.result[k]['label']['text'] = '-'
            self.result[k]['label']['fg'] = 'black'
        for k in self.entries.keys():
            self.entries[k]['entryVar'].set('')
        self.msg['text'] = ''
        self._update = False
        super().disButtons(event)


class lFrame3(cFrame):
    def __init__(self, parent, pos, name, spring):
        super().__init__(parent, pos, name, spring)
        self.cycles = DoubleVar()
        self.cycles.trace('w', self.solve)
        self.frame.grid_columnconfigure(1, minsize=1, weight=1)
        self.frame.grid_columnconfigure(2, minsize=1,  weight=1)
        self.labels = {}
        self.defUnit = 'mm'
        self.entries = OrderedDict([('10\u2075', {'value': 1e5, 'entry': None}),
                                    ('10\u2076', {'value': 1e6, 'entry': None}),
                                    ('10\u2077', {'value': 1e7, 'entry': None})
                                   ])

    def init_widget(self):
        Label(self.frame, text='Ciclos:').grid(column=0, row=0, sticky='we',
                                               columnspan=1)
        i = 1
        for k in self.entries.keys():
            rb = Radiobutton(self.frame, text=k, variable=self.cycles,
                             value=self.entries[k]['value'], state='disabled')
            rb.grid(sticky='ew', column=0, row=i, columnspan=1)
            self.entries[k]['entry'] = rb
            i += 1
        Label(self.frame, text='Deflexión máxima:').grid(column=1, row=0,
                                                         sticky='w',
                                                         columnspan=2,
                                                         pady=2, padx=5)
        Label(self.frame, text='Frecuencia máxima:').grid(column=1, row=2,
                                                          sticky='w',
                                                          columnspan=2,
                                                          pady=2, padx=5)
        self.labels['x'] = Label(self.frame, text='-')
        self.labels['x'].grid(column=1, row=1, sticky='n')
        self.labels['fmax'] = Label(self.frame, text='-')
        self.labels['fmax'].grid(column=1, row=3, sticky='n')
        self.cycles.set(1e6)

    def solve(self, *args):
        if self.spring.isSolved:
            res = self.spring.verifyDynamic(cycles=self.cycles.get())
            self.labels['x']['text'] = "{:.2f} {}".format(res['x'],
                                                          self.defUnit)
            self.labels['fmax']['text'] = "{:.2f} ciclos / min".\
                                          format(res['fmax'])

    def enaButtons(self, event):
        super().enaButtons(event)
        self.cycles.set(self.cycles.get())

    def disButtons(self, event):
        for k in self.labels.keys():
            self.labels[k]['text'] = '-'
        super().disButtons(event)


class consoleFrame(LabelFrame):
    def __init__(self, parent, name):
        self.parent = parent
        super().__init__(parent, text=name)
        self.grid_columnconfigure(0, weight=1)
        self.grid(column=0, row=2, sticky="nsew")
        self.text = Text(self, wrap='word', height=10)
        self.text.grid(column=0, row=0, sticky='nsew', padx=5,
                       pady=5)
        redir = StdoutRedirector(self.text)
        sys.stdout = redir


class subWindow2(subWindow):
    def __init__(self, parent, spring):
        super().__init__(parent, spring)
        self.grid_columnconfigure(0, weight=1)
        del self.lf1.cbEntries['fixing']
        del self.lf1.cbEntries['ending']
        del self.lf1.entries['Na']
        del self.lf1.entries['gap']
        del self.lf1.entries['p']
        del self.lf1.entries['Ls']
        self.lf1.entries['Lo']['text'] = 'Longitud del cuerpo:'
        self.lf1.entries['La'] = {'text': 'Longitud adicional:',
                                  'unit': 'mm', 'entry': None,
                                  'entryVar': StringVar()}
        self.lf1.entries['Ra'] = {'text': 'Radio gancho A:',
                                  'unit': 'mm', 'entry': None,
                                  'entryVar': StringVar()}
        self.lf1.entries['Rb'] = {'text': 'Radio curva gancho B:',
                                  'unit': 'mm', 'entry': None,
                                  'entryVar': StringVar()}
        self.lf2.result['stressA'] = {'unit': '% (en punto A)', 'label': None}
        self.lf2.result['stressB'] = {'unit': '% (en punto B)', 'label': None}


class subWindow3(subWindow):
    def __init__(self, parent, spring):
        super().__init__(parent, spring)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        del self.lf1.cbEntries['fixing']
        del self.lf1.cbEntries['ending']
        del self.lf1.entries['Na']
        del self.lf1.entries['gap']
        del self.lf1.entries['p']
        del self.lf1.entries['Ls']
        self.lf1.entries['L1'] = {'text': 'Longitud gancho 1:',
                                  'unit': 'mm', 'entry': None,
                                  'entryVar': StringVar()}
        self.lf1.entries['L2'] = {'text': 'Longitud gancho 2',
                                  'unit': 'mm', 'entry': None,
                                  'entryVar': StringVar()}
        self.lf2.entries['x']['unit'] = 'º'
        self.lf2.result['x']['unit'] = 'º'
        self.lf3.defUnit = 'º'


class Window(Frame):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(parent)
        self.init_window()

    def init_window(self):
        self.parent.title("SupMold: SpringCalc")
        self.grid(column=0, row=0, sticky="nwse")
        mainFrame = Frame(self, relief='raised', borderwidth=1)
        mainFrame.grid(column=0, row=0, sticky='nsew')
        closeButton = Button(mainFrame, text='Cerrar', command=self.appQuit)
        closeButton.grid(column=0, row=3, padx=5, pady=5)
        nb = Notebook(mainFrame)
        tab1 = Frame(nb)
        tab2 = Frame(nb)
        tab3 = Frame(nb)
        nb.add(tab1, text="Compresión")
        nb.add(tab2, text="Extensión")
        nb.add(tab3, text="Torsión")
        nb.grid(column=0, row=1, sticky='nsew', padx=5, pady=5)
        msg = consoleFrame(mainFrame, 'Mensages')
        dataB = resource_path('wires.db')
        if not os.path.isfile(dataB):
            self.centerWindow()
            messagebox.showerror("ERROR", "Base de datos {} inaccesible. "
                                 "Favor verificar permisos de lectura o "
                                 "ubicación de la misma".format(dataB))
            return
        self.sub1 = subWindow(tab1, Spring(database=dataB))
        self.sub1.init_widgets()
        self.sub2 = subWindow2(tab2, eSpring(database=dataB))
        self.sub2.init_widgets()
        self.sub3 = subWindow3(tab3, tSpring(database=dataB))
        self.sub3.init_widgets()
        self.centerWindow()
        nb.bind("<<NotebookTabChanged>>", self.tabChangedEvent)

    def tabChangedEvent(self, event):
        idx = event.widget.index("current")
        if idx == 0:
            self.sub1.lf1.entries['d']['entry'].focus_set()
        elif idx == 1:
            self.sub2.lf1.entries['d']['entry'].focus_set()
        elif idx == 2:
            self.sub3.lf1.entries['d']['entry'].focus_set()


    def appQuit(self):
        self.parent.destroy()

    def centerWindow(self):
        self.parent.update()
        w = self.parent.winfo_width()
        h = self.parent.winfo_height()
        sw = self.parent.winfo_screenwidth()
        sh = self.parent.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.parent.geometry('{}x{}+{}+{}'.format(w, h, x, y))


def main():
    multiprocessing.freeze_support()
    root = Tk()
    iconFile = resource_path('spring.ico')
    if os.name == 'nt':
        root.iconbitmap(iconFile)
    Window(root)
    root.mainloop()

if __name__ == "__main__":
    main()
