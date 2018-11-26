#!/bin/bash/env python
"""Superior Moldie, C.A.
   San Diego 2006, Venezuela
   by Alberto Vázquez
   v1.0.1"""
from math import pi, sqrt
import sqlite3 as sq
from sympy import Symbol, Add, Mul, Float, solve
from multiprocessing import Process, Queue
import os


class Spring:
    """Definition of class Spring. To fully define the Spring Class, three
    parameters should be given: ending, fixing and material.
    The possible values for those parameters are:
         -Ending: closed-ground, closed, open-ground and open. Where
                  closed-ground is the default value.
         -Fixing: fix-parallel, fix-pivot, both-pivot and hinged-free. Where
                  fix-parallel is the default value.
         -Material: A229, T302, A228, A231. A229 is the default value.
    Aditionally, named values passed as dictionary are required. Only the
    following parameters will be accepted:
         - d : wire gauge
         - DE : external diameter
         - DM : medium diameter
         - DI : internal diameter
         - Nt : total number of turns
         - Na : Active turns
         - p : spring's pitch
         - Lo : free length
         - Ls : solid length
    If different parameters to the list are given, they'll be ignored.
    If less than 4 parameters are given the attributes of the class would not
    be fully solved.

    ***NOTE: All the units given are in: mm, N, Kg, MPa, Hz"""
    def __init__(self, ending='closed-ground', fixing='fix-parallel',
                 material='A229', database='wires.db', **kwargs):
        if not os.path.isfile(database):
            raise FileNotFoundError("El archivo de base de dato no se "
                                    "encuentra disponible")
        self._db = database
        self._endList = ('closed-ground', 'closed', 'open-ground', 'open')
        self._fixList = ('fix-parallel', 'fix-pivot', 'both-pivot',
                         'hinged-free')
        self._matList = tuple(self._getData("SELECT MATERIAL FROM MATERIALS",
                                            ()))
        self.ending = self._checkInputVar(ending, self._endList)
        self.fixing = self._checkInputVar(fixing, self._fixList)
        self.material = self._checkInputVar(material, self._matList)
        self._setData((self._getData("SELECT DENSITY, SHEAR_MOD, ELAST_MOD, \
                      MAX_WORK_TEMP, HT_TEMP, HT_TIME FROM MATERIALS WHERE \
                      MATERIAL=?", (self.material,))), ['rho', 'G', 'E',
                                                        'maxT', 'htTemp',
                                                        'htTime'])
        self._paramNames = ['d', 'DE', 'DM', 'DI', 'Nt', 'Na', 'p', 'gap',
                            'Lo', 'Ls', 'C', 'w', 'fn', 'k']
        self._rstParams()

    def _checkInputValue(self, allowNeg=False, **kwargs):
        """General function to test input as integer or float, greater than
        zero"""
        for (k, v) in kwargs.items():
            try:
                aux = float(v)
            except ValueError:
                raise ValueError("Valor introducido {} = {} no es válido"
                                 .format(k, v))
            else:
                if not allowNeg and str(k) != 'gap' and aux <= 0:
                    raise ValueError('Número {} = {} es menor igual que cero'.
                                     format(k, v))
                elif str(k) == 'gap' and aux < 0:
                    raise ValueError('Número {} = {} es menor que cero'.
                                     format(k))
                else:
                    kwargs[k] = aux
        return kwargs

    def _checkInputVar(self, x, accepted):
        """General function to check if the option given is in the accepted
        list, and will return this value. If is not in the list, will raise
        an exception"""
        if x in accepted:
            return x
        else:
            raise ValueError("Valor dado {} no corresponde a las opciones "
                             "válidas". format(x))

    def _getData(self, instruction, tupVars):
        """Will connect to the database and execute the instruction, using
        variables in tupVars to filter. The result will be saved dinamically
        in variables created with the names (str) pased in the 'args'"""
        try:
            con = sq.connect(self._db)
        except:
            print("Base de datos no disponible, revisar permiso de lectura o "
                  "ubicación del archivo")
            return 1
        cur = con.cursor()
        cur.execute(instruction, tupVars)
        result = []
        while True:
            aux = cur.fetchone()
            if aux is None:
                break
            else:
                for i in aux:
                    result.append(i)
        con.close()
        if len(result) == 0:
            raise ValueError("El data buscado, no se encuentra en la base de "
                             "datos")
        return result

    def _setData(self, values, keys):
        """Take the values given  as lists and store them as a class parameters
        with the key name in keys"""
        for (k, v) in zip(keys, values):
            setattr(self, str(k), v)

    def _rstParams(self):
        """Return all the required variables to default state to resolve the
        equations"""
        self.isSolved = False
        for k in self._paramNames:
            setattr(self, k, Symbol(k))

    def _setEqs(self, kEq):
        """Generates the equations based on the ending type"""
        Eq = [self.DM - self.DE + self.d,
              self.DM - self.DI - self.d]
        if self.ending == 'closed-ground':
            Eq.append(self.Na - self.Nt + 2)
            Eq.append(self.p * self.Na - self.Lo + 2*self.d)
            Eq.append(self.Ls - self.d*self.Nt)
        elif self.ending == 'closed':
            Eq.append(self.Na - self.Nt + 2)
            Eq.append(self.p * self.Na - self.Lo + 3*self.d)
            Eq.append(self.Ls - self.d*(self.Nt + 1))
        elif self.ending == 'open-ground':
            Eq.append(self.Na - self.Nt + 1)
            Eq.append(self.p * self.Na - self.Lo)
            Eq.append(self.Ls - self.d*self.Nt)
        elif self.ending == 'open':
            Eq.append(self.Na - self.Nt)
            Eq.append(self.p * self.Na - self.Lo + self.d)
            Eq.append(self.Ls - self.d*(self.Nt + 1))
        Eq.extend([self.C*self.d - self.DM,
                   self.rho * (pi * self.d / 2)**2 * self.DM * self.Nt -
                   self.w, self.gap - self.p + self.d,
                   (self.d * sqrt(self.G)) / (sqrt(2*self.rho) * self.DM**2 *
                                              self.Na) - self.fn])
        Eq.extend(kEq)
        return Eq

    def checkUnresolved(self):
        """Check the number of parameters of the spring that are unresolved"""
        unresolved = []
        for (k, v) in self.__dict__.items():
            if type(v) is Symbol or type(v) is Add or type(v) is Mul:
                unresolved.append(k)
        return unresolved

    def _setParams(self, **kwargs):
        """Take the arguments given and if the name passed is in the list of
        attributes of the class, it will make these parameter equal to the
        value of the argument given."""
        self._rstParams()
        kwargs = self._checkInputValue(**kwargs)
        for (k, v) in kwargs.items():
            if str(k) in self._paramNames:
                setattr(self, str(k), v)

    def solveParams(self, time, **kwargs):
        """Function used to calculate the class attributes based on the kwargs,
        arguments given. This method should run as a parallel process for a
        maximum time of 'time' seconds. If the process is still alive, will be
        killed and a exception will be raised. If the process is finished
        succefully, the program will continue and the result of the methos
        will be saved as class parameters"""
        return_dict = Queue()
        p = Process(target=self._sParams, args=(return_dict,), kwargs=kwargs)
        p.start()
        p.join(time)
        if p.is_alive():
            p.terminate()
            raise ValueError("Timeout! No se puede resolver con los "
                             "parámetros dados")
            p.join()
        result = return_dict.get()
        self._setData(result.values(), result.keys())
        if len(self.checkUnresolved()) == 0:
            for (k, v) in self.__dict__.items():
                if type(v) is Float and k != 'gap' and v <= 0:
                    raise ValueError("Valor {} = {} es menor ó igual a cero".
                                     format(k, v))
                elif type(v) is Float and v < 0:
                    raise ValueError("Valor {} = {} es menor que cero".
                                     format(k, v))
                else:
                    self.isSolved = True

    def _sParams(self, return_dict, **kwargs):
        """Method that will be run in parallel"""
        self._setParams(**kwargs)
        result = (solve(self._setEqs(self._setK())))
        result = {**kwargs, **result[0]}
        return_dict.put(result)

    def verifyC(self):
        """Calculates the spring gauge-Diameter ratio, and through a warning
        if it's outside of the proper value. Will return 0 if the spring ratio
        is inside the interval; a positive number if is greater, and a negative
        one otherwise."""
        if type(self.C) is Symbol:
            raise ValueError("El valor de C no está definido.")
        if self.C >= 12:
            print("El índice del resorte ({:.2f}) es mayor del adecuado "
                  "(12.00), el diámetro del resorte debería ser menor o el "
                  "calibre mayor; ajustar. En caso de ser imposible, evitar "
                  "esmerilar para no empeorar su funcionamiento"
                  .format(self.C))
            return 1
        elif self.C <= 4:
            print("El índice del resorte ({:.2f}) es menor del adecuado "
                  "(4.00), el diámetro del resorte debería ser mayor o el "
                  "calibre menor; ajustar. En caso de ser imposible, evitar "
                  "esmerilar para no empeorar su funcionamiento"
                  .format(self.C))
            return -1
        return 0

    def verifyBuckling(self):
        """Calculates the maximum length allowed for the spring to avoid
        buckling."""
        if self.fixing == 'fix-parallel':
            alpha = 0.5
        elif self.fixing == 'fix-pivot':
            alpha = 0.707
        elif self.fixing == 'both-pivot':
            alpha = 1.0
        elif self.fixing == 'hinged-free':
            alpha = 2.0
        LoMax = 2.63 / alpha * self.DM
        if type(LoMax) is Mul:
            raise ValueError("Valor 'DM' aún no está definido")
        else:
            if self.Lo >= LoMax:
                print("La longitud del resorte dada: {:.2f} mm, provocará "
                      "pandeo. Se recomienda mantener el largo menor a "
                      "{:.2f} mm".format(self.Lo, LoMax))
            return 0
        return 1

    def _checkMaxDef(self, x):
        """Rerturn the value of deflexion, if the value given is lesser than
        the maximum deflextion. Otherwise return the last value."""
        return x if self.Lo - x > self.Ls else self.Lo - self.Ls

    def _setK(self):
        Eq = [self.G * self.d**4 / (8 * self.Na * self.DM**3) - self.k]
        return Eq

    def force(self, verbose=False, **kwargs):
        """Function to calculate the Force of the spring based on the deflexion
        given and the parameters of the spring. If the Force is given the
        deflexion is calculated. When the the values are outside of range, the
        maximum value will be returned.
        The return value is a dictionary with the value calculated."""
        unlock = True
        recheck = False
        vars = {'F': Symbol('F'), 'x': Symbol('x')}
        for (k, v) in kwargs.items():
            if k in vars.keys() and unlock:
                if k is 'x':
                    solvedKey = 'F'
                    v = self._checkInputValue(allowNeg=True, x=v)[k]
                    if v > 0:
                        aux = self._checkMaxDef(v)
                        if v != aux:
                            if verbose:
                                print("La deflexión dada es mayor a la máxima "
                                      "posible")
                            v = aux
                elif k is 'F':
                    solvedKey = 'x'
                    v = self._checkInputValue(allowNeg=True, F=v)[k]
                    recheck = True
                vars[k] = v
                unlock = False
        doWhile = True
        while doWhile:
            vars[solvedKey] = solve([self.k*vars['x'] - vars['F']])[Symbol(
                                                                solvedKey)]
            if recheck:
                if v > 0:
                    aux = self._checkMaxDef(vars['x'])
                    if vars[solvedKey] != aux:
                        if verbose:
                            print("La fuerza dada es mayor a la máxima "
                                  "posible")
                        vars[solvedKey] = aux
                    solvedKey = 'F'
                    vars[solvedKey] = Symbol(solvedKey)
                    recheck = False
                else:
                    doWhile = False
            else:
                doWhile = False
        return vars

    def _calcKw(self):
        """Solve the Wahl's curvature correction ratio"""
        return (((4*self.C - 1) / (4*self.C - 4)) + (0.615 / self.C))

    def _bodyStress(self, varz, *args):
        """Function to define the function to calculates the Walh's curvature
        correction factor for the stress in the body of the spring"""
        Kw = self._calcKw()
        Eq = [pi*varz['stress']*self.TS*self.d**3 - 8*Kw*self.DM*varz['F']]
        return Eq

    def _calcStress(self, Eq, verbose=False, *args, **kwargs):
        """Function to calculate the stress of the spring based on the force
        given, when this force excede the maximun possible force, this maximum
        value will be calculated and used to obtain the stress."""
        self._setData((self._getData("SELECT A, M FROM EQ_TS WHERE \
                                     WIRE_MAT = ? AND VALID_MIN <= ? AND \
                                     VALID_MAX >= ?", (self.material, self.d,
                                                       self.d,))), ['TS'])
        unlock = True
        recheck = False
        varz = {'stress': Symbol('stress'), 'F': Symbol('F')}
        for (k, v) in kwargs.items():
            if k in varz.keys() and unlock:
                if k is 'F':
                    solvedKey = 'stress'
                    v = self._checkInputValue(allowNeg=True, F=v)[k]
                    v = self.force(F=v)[k]
                elif k is 'stress':
                    solvedKey = 'F'
                    v = self._checkInputValue(allowNeg=True, stress=v)[k]
                    recheck = True
                varz[k] = v
                unlock = False
        condition = True
        while condition:
            varz[solvedKey] = solve(Eq(varz, *args))[Symbol(solvedKey)]
            if recheck:
                aux = self.force(**varz)
                if aux[solvedKey] != varz[solvedKey]:
                    if verbose:
                        print("El stress dado corresponde a un fuerza mayor a "
                              "la máxima posible")
                    varz[solvedKey] = aux[solvedKey]
                    solvedKey = 'stress'
                    varz[solvedKey] = Symbol(solvedKey)
                    recheck = False
                else:
                    condition = False
            else:
                condition = False
        return varz

    def stress(self, verbose=False, *args, **kwargs):
        """Calculate the stress on the body, based on the given Force, or
        calculate the force base on the given stress"""
        return self._calcStress(self._bodyStress, verbose, *args, **kwargs)

    def verifyDynamic(self, verbose=False, cycles=1e6):
        """Check the values for dynamic functioning of the spring: high number
        of cycles. Valid values for cycles are 1e5, 1e6, 1e7, with 1e6 as
        default value"""
        if type(self.fn) is Symbol:
            raise ValueError("El valor de fn no está definido.")
        if self.fixing == "fix-parallel" or self.fixing == "both-pivot":
            f = self.fn / 13 * 60
        elif self.fixing == "fix-pivot" or self.fixing == "hinged-free":
            f = self.fn / 26 * 60
        if self.material == "A229" or self.material == "A228" or self.material\
           == "T302" or self.material == "A227":
            if cycles == 1e5:
                TS = 0.36
                cyk = '\u2075'
            elif cycles == 1e6:
                TS = 0.33
                cyk = '\u2076'
            elif cycles == 1e7:
                TS = 0.30
                cyk = '\u2077'
            else:
                TS = 0.33
                cyk = '\u2076'
        elif self.material == "A231" or self.material == "A401":
            if cycles == 1e5:
                TS = 0.42
                cyk = '\u2075'
            elif cycles == 1e6:
                TS = 0.40
                cyk = '\u2076'
            elif cycles == 1e7:
                TS = 0.38
                cyk = '\u2077'
            else:
                TS = 0.40
                cyk = '\u2076'
        aux = self.force(**self.stress(stress=TS))
        if verbose:
            print("La frecuencia de trabajo debe ser menor a {:.2f} "
                  "ciclos / min". format(f))
            print("Para la vida útil definida (10{} ciclos) la deflexión del "
                  "resorte no debe superar los {:.2f} mm".
                  format(cyk, aux['x']))
            print("La vida útil mínima estimada del resorte será: {:.2f} "
                  "minutos".format(cycles / f))
        return {'cycles': cycles, 'x': aux['x'], 'fmax': f}

    def showParams(self):
        """Function to print all the paramenters current defined in the class
        """
        print("Los valores del resorte actualmente definidos son:")
        for (k, v) in sorted(self.__dict__.items()):
            if not k.startswith("_"):
                if type(v) is float or type(v) is Float or type(v) is int:
                    print("{0:10}{1:15.3g}".format(k, float(v)))
                else:
                    print("{0:10}{1:15}".format(k, str(v).rjust(15)))


class eSpring(Spring):
    """Extension springs, are similar to compression one, but the turns, are
    without any separation (gap = 0) the type of ending is 'open' and aren't
    fixed to parallel plates (both ends pivot)"""
    def __init__(self, material='A229', database='wires.db', **kwargs):
        super().__init__(ending='open', fixing='both-pivot',
                         material=material, database=database, **kwargs)
        self.La = 0
        self.Ra = 0
        self.Rb = 0

    def solveParams(self, time, **kwargs):
        """Define gap as zero, ignoring any value given"""
        kwargs['gap'] = 0
        super().solveParams(time, **kwargs)
        self.w = self.w + self.addWeight()
        if self.Ra == 0:
            self.Ra = self.DM
        if self.Rb == 0:
            self.Rb = self.DM

    def _rstParams(self):
        """Return all the required variables to default state to resolve the
        equations"""
        super()._rstParams()
        self.gap = 0

    def force(self, verbose=False, **kwargs):
        for (k, v) in kwargs.items():
            kwargs[k] = -v
        result = super().force(verbose, **kwargs)
        for (k, v) in result.items():
            result[k] = -v
        return result

    def stress(self, verbose=False, *args, **kwargs):
        """Calculate the stress on the body, based on the given Force, or
        calculate the force base on the given stress"""
        result = self._calcStress(self._bodyStress, verbose, *args, **kwargs)
        aux = result.copy()
        del aux['stress']
        hookA = self._calcStress(self._hookStressA, verbose, *args, **aux)
        hookB = self._calcStress(self._hookStressB, verbose, *args, **aux)
        result = {**result, **{'stressA': hookA['stress'],
                               'stressB': hookB['stress']}}
        return result

    def _hookStressA(self, varz):
        """Set the equations for the bending stress on the point A in the
        spring's hook"""
        C1 = 2 * self.Ra / self.d
        if C1 <= 1:
            raise ValueError("Valor de C1 muy pequeño")
        Ka = (4*C1**2 - C1 - 1) / (4*C1*(C1 - 1))
        Eq = [(32 * Ka * self.DM * varz['F'] / (pi * self.d**3)) +
              (4 * varz['F'] / (pi * self.d**2)) - varz['stress'] * self.TS]
        return Eq

    def _hookStressB(self, varz):
        """Define the equations for the torsion stress in the spring's hook"""
        C2 = 2 * self.Rb / self.d
        if C2 <= 4:
            raise ValueError("Valor de C1 muy pequeño")
        Kb = (4*C2 - 1) / (4*C2 - 4)
        Eq = [16 * varz['F'] * self.DM * Kb / (pi * self.d**3) -
              varz['stress'] * self.TS]
        return Eq

    def addWeight(self):
        """Method to calculate the additional weight of the spring, due of
        the hooks; so the total weight of the spring will be
        'self.w + _addWeight(La)' where La is all the additional length of the
        hooks (no including the 2 turns that forms them)"""
        if self.isSolved:
            '''La is the additional length of the hooks'''
            aux = self.La + self.DM * pi * 2
            wAdd = self.d**2 * pi * self.rho * aux / 4
            return wAdd

    def verifyBuckling(self):
        """Make verifyBuckling method a dummy one"""
        pass

    def stressA(self, verbose=False, **kwargs):
        """Calculates the stress on the point A of the springs's hook based on
        the given force. Or calculates the force based on the given stress."""
        return self._calcStress(self._hookStressA, verbose, **kwargs)

    def stressB(self, verbose=False, **kwargs):
        """Calculates the stress on the point B of the springs's hook based on
        the given force. Or calculates the force based on the given stress."""
        return self._calcStress(self._hookStressB, verbose, **kwargs)

    def verifyDynamic(self, verbose=False, cycles=1e6):
        """Run a verification of the dynamic stress for the spring body
        and hooks. Will return the minimum deflexion so all three stress
        are below maximum"""
        if type(self.fn) is Symbol:
            raise ValueError("El valor de fn no está definido.")
        f = self.fn / 13 * 60
        if cycles == 1e5:
            tsBody = 0.36
            tsHookT = 0.34
            tsHookF = 0.51
            cyk = '\u2075'
        elif cycles == 1e6:
            tsBody = 0.33
            tsHookT = 0.30
            tsHookF = 0.47
            cyk = '\u2076'
        elif cycles == 1e7:
            tsBody = 0.30
            tsHookT = 0.28
            tsHookF = 0.45
            cyk = '\u2077'
        else:
            tsBody = 0.33
            tsHookT = 0.30
            tsHookF = 0.47
            cyk = '\u2076'
        sBody = self.force(**self._calcStress(self._bodyStress, stress=tsBody))
        sBend = self.force(**self._calcStress(self._hookStressA,
                                              stress=tsHookF))
        sTors = self.force(**self._calcStress(self._hookStressB,
                                              stress=tsHookT))
        aux = [sBody['x'], sBend['x'], sTors['x']]
        aux.sort()
        if verbose:
            print("La frecuencia de trabajo debe ser menor a {:.2f} "
                  "ciclos / min". format(f))
            print("Para la vida útil definida (10{} ciclos) la deflexión del "
                  "resorte no debe superar los {:.2f} mm".
                  format(cyk, aux[0]))
            print("La vida útil mínima estimada del resorte será: {:.2f} "
                  "minutos".format(cycles / f))
        return {'cycles': cycles, 'x': aux[0], 'fmax': f}


class tSpring(eSpring):
    """Define a torsion spring as a compresion one but with ending 'open'
    and no fixing. To define the torsion spring the length of the hooks are
    required to compute the torsional mometum of the spring.
    ***NOTE The deflexion of the spring is not given in mm like the compression
    and extension springs, but in degrees."""
    def __init__(self, L1=0, L2=0, material='A229', database='wires.db',
                 **kwargs):
        self.L1 = L1
        self.L2 = L2
        super().__init__(material=material, database=database, **kwargs)
        del self.Ra
        del self.Rb
        del self.La

    # def _Nc(self):
    #     """Calculate the equivalent of turns due the length of the hooks"""
    #     return (self.Nt + ((self.L1 + self.L2) / (3 * pi * self.DM)))

    def _setK(self):
        """Calculates the constant of the torsion spring"""
        Eq = [self.E * self.d**4 / (3.888E3 * self.DM * (self.Nt + ((self.L1 +
                                    self.L2) / (3 * pi * self.DM)))) - self.k]
        return Eq

    def solveParams(self, time, **kwargs):
        """Define gap as zero, ignoring any value given"""
        kwargs['gap'] = 0
        super(eSpring, self).solveParams(time, **kwargs)
        self.w = self.w + self.addWeight()

    def _bodyStress(self, varz):
        """Generate the equation of the spring's body stress"""
        Kb = (4*self.C - 1) / (4*self.C - 4)
        Eq = [32 * varz['F'] * Kb / (pi * self.d**3) -
              varz['stress'] * self.TS]
        return Eq

    def stress(self, verbose=False, *args, **kwargs):
        """Calculate the stress on the body, based on the given Force, or
        calculate the force base on the given stress"""
        return self._calcStress(self._bodyStress, verbose, *args, **kwargs)

    def stressA(self):
        raise AttributeError("'tSpring' has no attibute 'stressA'")

    def stressB(self):
        raise AttributeError("'tSpring' has no attibute 'stressB'")

    def addWeight(self):
        if self.isSolved:
            '''La is the additional length of the hooks'''
            La = self.L1 + self.L2
            wAdd = self.d**2 * pi * self.rho * La / 4
            return wAdd

    def verifyDynamic(self, verbose=False, cycles=1e6):
        """Verify that the stress during dynamical fuction of the spring,
        is under the maximum values"""
        if type(self.fn) is Symbol:
            raise ValueError("El valor de fn no está definido.")
        f = self.fn / 13 * 60
        if self.material == 'A227' or self.material == 'A228' or \
           self.material == 'A229' or self.material == 'T302':
                if cycles == 1e5:
                    tsBody = 0.53
                    cyk = '\u2075'
                elif cycles == 1e6:
                    tsBody = 0.50
                    cyk = '\u2076'
                else:
                    tsBody = 0.50
                    cyk = '\u2076'
        elif self.material == 'A231' or self.material == 'A401':
                if cycles == 1e5:
                    tsBody = 0.55
                    cyk = '\u2075'
                elif cycles == 1e6:
                    tsBody = 0.53
                    cyk = '\u2076'
                else:
                    tsBody = 0.53
                    cyk = '\u2076'
        aux = self.force(**self.stress(stress=tsBody))
        if verbose:
            print("La frecuencia de trabajo debe ser menor a {:.2f} "
                  "ciclos / min". format(f))
            print("Para la vida útil definida (10{} ciclos) la deflexión del "
                  "resorte no debe superar los {:.2f}º".
                  format(cyk, aux['x']))
            print("La vida útil mínima estimada del resorte será: {:.2f} "
                  "minutos".format(cycles / f))
        return {'cycles': cycles, 'x': aux['x'], 'fmax': f}


def main():
    print("*** COMPRESSION ***")
    s = Spring(material='A227', fixing='fix-pivot')
    s.solveParams(d=1, DE=10, Nt=8, Lo=20)
    print(s.force(F=28))
    print(s.stress(stress=0.4))
    s.verifyC()
    s.verifyBuckling()
    print(s.verifyDynamic(cycles=1e7))

    print("*** EXTENSION ***")
    es = eSpring(material='T302')
    es.solveParams(d=1, DE=10, Lo=20)
    print(es.force(F=20))
    print(es.stress(F=20))
    print(es.verifyDynamic())
    es.verifyC()

    print("*** TORSION ***")
    ts = tSpring(materia='A228')
    print(ts._paramNames)
    ts.showParams()
    ts.solveParams(d=1, DE=10, Nt=8)
    ts.showParams()
    print(ts.force(F=20))
    print(ts.stress(stress=0.85))
    ts.verifyC()
    print(ts.verifyDynamic())


if __name__ == '__main__':
    main()
