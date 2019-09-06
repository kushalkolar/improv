from queue import Empty
import time

import logging; logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Module():
    '''Abstract class for a module that Nexus
       controls and interacts with.
       Needs to have a store and links for communication
       Also needs at least a setup and run function
    '''
    def __init__(self, name, links={}, **kwargs):
        ''' Require a name for multiple instances of the same module/class
            Create initial empty dict of Links for easier referencing
        '''
        self.name = name
        self.links = links
        self.done = False #Needed?

        self.lower_priority = False 

        # start with no explicit data queues.             
        # q_in and q_out are for passing ID information to access data in the store
        self.q_in = None
        self.q_out = None

    def __repr__(self):
        ''' Return this instance name and links dict
        '''
        return self.name+': '+str(self.links.keys())

    def setStore(self, client):
        '''Set client interface to the store
        '''
        self.client = client

    def setLinks(self, links):
        ''' General full dict set for links
        '''
        self.links = links

    def setCommLinks(self, q_comm, q_sig):
        ''' Set explicit communication links to/from Nexus (q_comm, q_sig)
            q_comm is for messages from this module to Nexus
            q_sig is signals from Nexus and must be checked first
        '''
        self.q_comm = q_comm
        self.q_sig = q_sig
        self.links.update({'q_comm':self.q_comm, 'q_sig':self.q_sig})

    def setLinkIn(self, q_in):
        ''' Set the dedicated input queue
        '''
        self.q_in = q_in
        self.links.update({'q_in':self.q_in})

    def setLinkOut(self, q_out):
        ''' Set the dedicated output queue
        '''
        self.q_out = q_out
        self.links.update({'q_out':self.q_out})

    def addLink(self, name, link):
        ''' Function provided to add additional data links by name
            using same form as q_in or q_out
            Must be done during registration and not during run
        '''
        self.links.update({name:link})
        # User can then use: self.my_queue = self.links['my_queue'] in a setup fcn,
        # or continue to reference it using self.links['my_queue']

    def getLinks(self):
        ''' Returns dictionary of links
        '''
        return self.links

    def setup(self):
        ''' Essenitally the registration process
            Can also be an initialization for the module
            options is a list of options, can be empty
        '''
        raise NotImplementedError

    def run(self):
        ''' Must run in continuous mode
            Also must check q_sig either at top of a run-loop
            or as async with the primary function
        '''
        raise NotImplementedError

        ''' Suggested implementation for synchronous running: see RunManager class below
        TODO: define async example that checks for signals _while_ running
        '''

    def changePriority(self):
        ''' Try to lower this module's priority
            Only changes priority if lower_priority is set
            TODO: Only works on unix machines. Add Windows functionality
        '''
        if self.lower_priority is True:
            import os, psutil
            p = psutil.Process(os.getpid())
            p.nice(19) #lowest as default
            logger.info('Lowered priority of this process: {}'.format(self.name))
            print('Lowered ', os.getpid(), ' for ', self.name)


class Spike():
    ''' Class containing definition of signals Nexus uses
        to communicate with its modules
        TODO: doc each of these with expected handling behavior
        NOTE: add functionality as class objects..? Any advantage to this?
    '''
    @staticmethod
    def run():
        return 'run'

    @staticmethod
    def quit():
        return 'quit'

    @staticmethod
    def pause():
        return 'pause'

    @staticmethod
    def resume():
        return 'resume'

    @staticmethod
    def reset(): #TODO
        return 'reset'
    
    @staticmethod
    def load():
        return 'load'

    @staticmethod
    def setup():
        return 'setup'

    @staticmethod
    def ready():
        return 'ready'


class RunManager():
    ''' TODO: Update logger messages with module's name
    TODO: make async version of runmanager
    '''
    def __init__(self, name, runMethod, setup, q_sig, q_comm):
        self.run = False
        self.config = False
        self.runMethod = runMethod
        self.setup = setup
        self.q_sig = q_sig
        self.q_comm = q_comm
        self.moduleName = name

        #TODO make this tunable
        self.timeout = 0.000001

    def __enter__(self):
        self.start = time.time()

        while True:
            if self.run:
                try:
                    self.runMethod() #subfunction for running singly
                except Exception as e:
                    logger.error('Module '+self.moduleName+' exception during run: {}'.format(e))
            elif self.config:
                try:
                    self.setup() #subfunction for setting up the module
                    self.q_comm.put([Spike.ready()])
                except Exception as e:
                    logger.error('Module '+self.moduleName+' exception during setup: {}'.format(e))  
                    raise Exception
                self.config = False #Run once
            try: 
                signal = self.q_sig.get(timeout=self.timeout)
                if signal == Spike.run(): 
                    self.run = True
                    logger.warning('Received run signal, begin running')
                elif signal == Spike.setup():
                    self.config = True
                elif signal == Spike.quit():
                    logger.warning('Received quit signal, aborting')
                    break
                elif signal == Spike.pause():
                    logger.warning('Received pause signal, pending...')
                    self.run = False
                elif signal == Spike.resume(): #currently treat as same as run
                    logger.warning('Received resume signal, resuming')
                    self.run = True
            except Empty as e:
                pass #no signal from Nexus
        return None #Status...?


    def __exit__(self, type, value, traceback):
        logger.info('Ran for '+str(time.time()-self.start)+' seconds')
        logger.warning('Exiting RunManager')
        return None