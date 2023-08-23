import sys
import scipy.io as mat
import time
import numpy as np
import getpass

from mnc import myarx as a
from lwa_f import snap2_feng_etcd_client

# Constants
DELAY_OFFSET = 10 # minimum delay
ADC_CLOCK = 196000000    # sampling clock frequency, Hz
ETCDHOST = 'etcdv3service.sas.pvt'
snaps = range(1,12)

def dsig2feng(digitalSignal): # From digital sig num calculate F-unit location and signal
    funit = int(digitalSignal/64) + 1  # location, 1:11
    fsig = digitalSignal % 64          # FPGA signal number, 0:63
    return (funit,fsig)

ec = snap2_feng_etcd_client.Snap2FengineEtcdControl(ETCDHOST)
print('Connected to ETCD host %s' % ETCDHOST)


class Settings():
    """ Class to handle settings and configuration.
    Initially defined as from reading of matlab file created by Larry.
    Ultimately, can be generalized to include etcd reading.
    """

    def __init__(self, filename=None):
        """ Read configuration data file """

        if filename is not None:
            config = mat.loadmat(filename, squeeze_me=True)
            print('Read data file',sys.argv[1])
            print('Data file internal time: ',time.asctime(time.gmtime(config['time'])))
            cfgkeys = config.keys()
        else:
#            config = <read from etcd>

    def load_feng(self):
        """ Load settings for f-engine to the SNAP2 boards.
        """
        
        print('Loading settings to SNAP2 boards:', snaps)

        #=================================
        # SET F ENGINE FFT SHIFT SCHEDULE
        #---------------------------------

        if 'fftShift' in cfgkeys:
            fftshift = config['fftShift']
        else:
            fftshift = 0x1FFC

        for i in snaps:
            ec.send_command(i,'pfb','set_fft_shift',kwargs={'shift':int(fftshift)})
        print('All FFT shifts set to','%04X' % fftshift)


        #=====================================
        # LOAD F ENGINE EQUALIZATION FUNCTIONS
        #-------------------------------------

        coef = config['coef']   # must include this key
        dsigDone = []
        print('LOADING EQUALIZATION COEFFICIENTS')

        k = 'eq0'   # coax length = ref+-50m
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                if not loc[0] in snaps: continue
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(int(loc[1])),'coeffs':coef[0].tolist()})
                dsigDone.append(i)
            print('eq0:',dsig)

        k = 'eq1'   # coax: shortest
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                if not loc[0] in snaps: continue
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[1].tolist()})
                dsigDone.append(i)
            print('eq1:',dsig)

        k = 'eq2'   # coax: next 40m
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                if not loc[0] in snaps: continue
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[2].tolist()})
                dsigDone.append(i)
            print('eq2:',dsig)

        k = 'eq3'   # coax: next 40m
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                if not loc[0] in snaps: continue
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[3].tolist()})
                dsigDone.append(i)
            print('eq3:',dsig)

        k = 'eq4'   # coax: next 40m
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[4].tolist()})
                dsigDone.append(i)
            print('eq4:',dsig)

        k = 'eq5'   # coax: longest
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                if not loc[0] in snaps: continue        
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[5].tolist()})
                dsigDone.append(i)
            print('eq5:',dsig)

        k = 'eq6'   # fiber
        if k in cfgkeys:
            dsig = config[k]
            for i in dsig:
                loc = dsig2feng(i)
                if not loc[0] in snaps: continue
                ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[6].tolist()})
                dsigDone.append(i)
            print('eq6:',dsig)

        for i in range(704):  # all others
            if i in dsigDone: continue
            loc = dsig2feng(i)
            if not loc[0] in snaps: continue    
            ec.send_command(loc[0],'eq','set_coeffs',kwargs={'stream':int(loc[1]),'coeffs':coef[0].tolist()})
    
        #=============================
        # LOAD F ENGINE DELAY SETTINGS
        #-----------------------------

        if 'delay_dsig' in config.keys():
            delays_ns = np.array(config['delay_dsig']) # delays in order of digital sig No., nanoseconds
    
            max_delay_ns = delays_ns.max()
            delays_clocks = np.round(delays_ns*1e-9 * ADC_CLOCK).astype(int)
            max_delay_clocks = delays_clocks.max()

            relative_delays_clocks = max_delay_clocks - delays_clocks
            max_relative_delay_clocks = delays_clocks.max()

            delays_to_apply_clocks = relative_delays_clocks + DELAY_OFFSET

            print('LOADING DELAYS')
            print('Maximum delay: %f ns' % max_delay_ns)
            print('Maximum delay: %d ADC clocks' % max_delay_clocks)
            print('Maximum relative delay: %d ADC clocks' % max_relative_delay_clocks)
            print('Maximum delay to be applied: %d ADC clocks' % delays_to_apply_clocks.max())
            print('Minimum delay to be applied: %d ADC clocks' % delays_to_apply_clocks.min())

            for dsig in range(len(delays_ns)):
                sig = dsig2feng(dsig)
                if not sig[0] in snaps: continue
                snap_id = sig[0]
                input_id = sig[1]
                ec.send_command(snap_id, 'delay', 'set_delay', kwargs={'stream':input_id, 'delay':int(delays_to_apply_clocks[dsig])})

        #============================
        # SET UNUSED F INPUTS TO ZERO
        #----------------------------

        print('SETTING UNUSED F ENG INPUTS TO ZERO.')
        if 'unused' in cfgkeys:
            unused = config['unused']
        else:
            unused = np.array([0]*704)
        for i in range(704):
            sig = dsig2feng(i)
            if not sig[0] in snaps: continue       
            snap_id = sig[0]
            input_id = sig[1]
            if unused[i]==True:
                ec.send_command(snap_id, 'input', 'use_zero', kwargs={'stream':input_id})
            else:
                ec.send_command(snap_id, 'input', 'use_adc', kwargs={'stream':input_id})

        print('Set',sum(unused),'inputs to use_zero and',sum(1-unused),'inputs to use_adc.')

    def load_arx(self):
        """ Load settings for ARX
        """
        #======================
        # NOW LOAD ARX SETTINGS
        #----------------------

        adrs = config['adrs']
        settings = config['settings']
        print('LOADING ARX SETTINGS')
        print('addresses: ',adrs)

        for i in range(len(adrs)):
            codes = ''
            for j in range(16):
                s = settings[i][j]
                codes += a.chanCode(s[0],s[1],s[2],s[3])
            try:
                a.raw(adrs[i],'SETA'+codes)
                print('Loaded: ',adrs[i],codes)
            except:
                continue

    def update_log(self, path='/home/pipeline/proj/lwa-shell/mnc_python/data/'):
        """ Add line to logging file
        """

        with open(path+'arxAndF-settings.log','a') as f:
            t = time.time()
            print(time.asctime(time.gmtime(t)), t, getpass.getuser(), sys.argv[1], config['time'], sep='\t',file=f)



def update(filename="data/20230721-settingsAll-night.mat"):
    settings = Settings(filename)
    settings.load_feng()
    settings.load_arx()
    settings.update_log()
