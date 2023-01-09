import time
import os
import pytest
import logging

from improv.nexus import Nexus
from improv.actor import Actor
from improv.store import Store

@pytest.fixture
def setdir():
    prev = os.getcwd()
    os.chdir(os.path.dirname(__file__) + '/configs')
    yield None
    os.chdir(prev)

@pytest.fixture
def sample_nex(setdir):
    setdir
    nex = Nexus("test")
    nex.createNexus(file='good_config.yaml', store_size=4000)
    yield nex
    nex.destroyNexus()

# @pytest.fixture
# def setup_store(setdir):
#     """ Fixture to set up the store subprocess with 10 mb.

#     This fixture runs a subprocess that instantiates the store with a 
#     memory of 10 megabytes. It specifies that "/tmp/store/" is the 
#     location of the store socket.

#     Yields:
#         Store: An instance of the store.

#     TODO:
#         Figure out the scope.
#     """
#     setdir
#     p = subprocess.Popen(
#         ['plasma_store', '-s', '/tmp/store/', '-m', str(10000000)],\
#         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#     store = Store(store_loc = "/tmp/store/")
#     yield store
#     p.kill()

def test_init(setdir):
    setdir
    # store = setup_store
    nex = Nexus("test")
    assert str(nex) == "test"


def test_createNexus(setdir):
    setdir
    nex = Nexus("test")
    nex.createNexus(file = "good_config.yaml")
    assert list(nex.comm_queues.keys()) == ["GUI_comm", "Acquirer_comm", "Analysis_comm"]
    assert list(nex.sig_queues.keys()) == ["Acquirer_sig", "Analysis_sig"]
    assert list(nex.data_queues.keys()) == ["Acquirer.q_out", "Analysis.q_in"]
    assert list(nex.actors.keys()) == ["Acquirer", "Analysis"]
    assert list(nex.flags.keys()) == ["quit", "run", "load"] 
    assert nex.processes == []
    nex.destroyNexus()
    assert True

def test_loadConfig(sample_nex):
    nex = sample_nex 
    nex.loadConfig('good_config.yaml')
    assert set(nex.comm_queues.keys()) == set(["Acquirer_comm", "Analysis_comm", "GUI_comm"])

#delete this comment later
@pytest.mark.skip(reason="unfinished")
def test_startNexus(sample_nex):
    nex = sample_nex
    nex.startNexus()
    assert [p.name for p in nex.processes] == ["Acquirer", "Analysis"]

# @pytest.mark.skip(reason="This test is unfinished")
@pytest.mark.parametrize("cfg_name, actor_list, link_list", [
    ("good_config.yaml", ["Acquirer", "Analysis"], ["Acquirer_sig", "Analysis_sig"]),
    ("simple_graph.yaml", ["Acquirer", "Analysis"], ["Acquirer_sig", "Analysis_sig"]),
    ("complex_graph.yaml", ["Acquirer", "Analysis", "InputStim"], ["Acquirer_sig", "Analysis_sig", "InputStim_sig"])
])
def test_config_construction(cfg_name, actor_list, link_list, setdir):
    """ Tests if constructing a nexus based on the provided config has the right structure.
    
    After construction based on the config, this 
    checks whether all the right actors are constructed and whether the 
    links between them are constructed correctly. 
    """

    setdir

    nex = Nexus("test")
    nex.createNexus(file = cfg_name)
    logging.info(cfg_name)

    # Check for actors

    act_lst = list(nex.actors)
    lnk_lst = list(nex.sig_queues)

    nex.destroyNexus()

    assert actor_list == act_lst
    assert link_list == lnk_lst 
    act_lst = []
    lnk_lst = []
    assert True

def test_single_actor(setdir):
    setdir
    nex = Nexus("test")
    with pytest.raises(AttributeError):
        nex.createNexus(file="single_actor.yaml")

    nex.destroyNexus()

def test_cyclic_graph(setdir):
    setdir
    nex = Nexus("test")
    nex.createNexus(file="cyclic_config.yaml")
    assert True
    nex.destroyNexus()

def test_blank_cfg(setdir, caplog):
    setdir
    nex = Nexus("test")
    with pytest.raises(TypeError):
        nex.createNexus(file="blank_file.yaml")
    assert any(["The config file is empty" in record.msg for record in list(caplog.records)])
    nex.destroyNexus()

# def test_hasGUI_True(setdir):
#     setdir
#     nex = Nexus("test")
#     nex.createNexus(file="basic_demo_with_GUI.yaml")

#     assert True
#     nex.destroyNexus()

# @pytest.mark.skip(reason="This test is unfinished.")
# def test_hasGUI_False():
#     assert True

@pytest.mark.skip(reason="unfinished")
def test_queue_message(setdir, sample_nex):
    setdir
    nex = sample_nex
    nex.startNexus()
    time.sleep(20)
    nex.setup()
    time.sleep(20)
    nex.run()
    time.sleep(10)
    acq_comm = nex.comm_queues["Acquirer_comm"]
    acq_comm.put("Test Message")
    
    assert nex.comm_queues == None 
    nex.destroyNexus()
    assert True

@pytest.mark.asyncio
@pytest.mark.skip(reason="This test is unfinished.")
async def test_queue_readin(sample_nex, caplog):
    nex = sample_nex
    nex.startNexus()
    # cqs = nex.comm_queues
    # assert cqs == None
    assert [record.msg for record in caplog.records] == None
    # cqs["Acquirer_comm"].put('quit')
    # assert "quit" == cqs["Acquirer_comm"].get()
    # await nex.pollQueues() 
    assert True

@pytest.mark.skip(reason="This test is unfinished.")
def test_queue_sendout():
    assert True

@pytest.mark.skip(reason="This test is unfinished.")
def test_run_sig():
    assert True

@pytest.mark.skip(reason="This test is unfinished.")
def test_setup_sig():
    assert True

@pytest.mark.skip(reason="This test is unfinished.")
def test_quit_sig():
    assert True

@pytest.mark.skip(reason="This test is unfinished.")
def test_usehdd_True():
    assert True

@pytest.mark.skip(reason="This test is unfinished.")
def test_usehdd_False():
    assert True

def test_startstore(caplog):
    nex = Nexus("test")
    nex._startStore(10000) # 10 kb store

    assert any(["Store started successfully" in record.msg for record in caplog.records])
    
    nex._closeStore()
    assert True

def test_closestore(caplog):
    nex = Nexus("test")

    nex._startStore(10000)
    nex._closeStore()

    assert any("Store closed successfully" in record.msg for record in caplog.records)

    # write to store

    with pytest.raises(AttributeError):
        nex.p_Store.put("Message in", "Message in Label")
    
    assert True

@pytest.mark.skip(reason="unfinished")
def test_actor_sub(setdir, capsys, monkeypatch):

    
    setdir
    monkeypatch.setattr("improv.nexus.input", lambda: "setup\n")
    cfg_file = "sample_config.yaml"
    nex = Nexus("test")

    
    nex.createNexus(file = cfg_file, store_size=4000)
    print("Nexus Created")
    
    nex.startNexus()
    print("Nexus Started")
    # time.sleep(5)
    # print("Printing...")
    # subprocess.Popen(["setup"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # time.sleep(2)
    # subprocess.Popen(["run"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # time.sleep(5)
    # subprocess.Popen(["quit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    nex.destroyNexus()
    assert True