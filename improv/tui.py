import asyncio
import zmq.asyncio as zmq
from zmq import PUB, SUB, SUBSCRIBE, REQ, REP
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.screen import Screen
from textual.widgets import Header, Footer, TextLog, Input, Button, Static
from textual.message import Message, MessageTarget
from improv.link import Link
import logging; logger = logging.getLogger(__name__)
from zmq.log.handlers import PUBHandler
logger.setLevel(logging.INFO)  

class SocketLog(TextLog):
    def __init__(self, port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        context = zmq.Context()
        self.socket = context.socket(SUB)
        self.socket.connect("tcp://%s" % str(port))
        self.socket.setsockopt_string(SUBSCRIBE, "")

    class Echo(Message):
        def __init__(self, sender, value) -> None:
            super().__init__(sender)
            self.value = value

    async def poll(self):
        try:
            ready = await self.socket.poll(10)
            if ready:
                payload = await self.socket.recv()
                msg = payload.decode('utf-8')
                self.write(msg)
                await self.emit(self.Echo(self, msg))
        except asyncio.CancelledError:
            pass

    async def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.poller = self.set_interval(1/60, self.poll)

class QuitScreen(Screen):
    def compose(self) -> ComposeResult:
        quit_str = ("Are you sure you want to quit? "
        "The server has not been stopped, and the process "
        "may continue to run in the background. "
        "To exit safely, enter 'quit' into the command console. "
        )

        yield Grid(
            Static(quit_str, id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
        else:
            self.app.pop_screen()

class TUI(App, inherit_bindings=False):
    """
    View class for the text user interface. Implemented as a Textual app.
    """
    def __init__(self, control_port, output_port, logging_port):
        super().__init__()
        self.control_port = TUI._sanitize_addr(control_port)
        self.output_port = TUI._sanitize_addr(output_port)
        self.logging_port = TUI._sanitize_addr(logging_port)

        context = zmq.Context()
        self.control_socket = context.socket(REQ)
        self.control_socket.connect("tcp://%s" % self.control_port)

        logger.info('Text interface initialized')

    CSS_PATH = "tui.css"
    BINDINGS = [
               ("tab", "focus_next", "Focus Next"),
               ("ctrl+c", "request_quit", "Emergency Quit")
    ]

    @staticmethod
    def _sanitize_addr(input):
        if isinstance(input, int):
            return "localhost:%s" % str(input)
        elif ':' in input:
            return input
        else:
            return "localhost:%s" % input

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Grid(
            Header(),
            SocketLog(self.output_port, id="console"),
            Input(),
            SocketLog(self.logging_port, id="log"),
            Footer(),
            id="main"
        )

    async def poll_controller(self):
        try:
            ready = await self.control_socket.poll(10)
            if ready:
                reply = await self.control_socket.recv_multipart()
                msg = reply[0].decode('utf-8')
                self.query_one("#console").write(msg)

        except asyncio.CancelledError:
            pass


    async def on_mount(self):
        self.poller = self.set_interval(1/60, self.poll_controller)
        self.set_focus(self.query_one(Input))
    
    async def on_input_submitted(self, message):
        self.query_one(Input).value = ""
        self.query_one("#console").write(message.value)
        await self.control_socket.send_string(message.value)
    
    async def on_socket_log_echo(self, message):
        if message.sender.id == 'console' and message.value == 'QUIT':
            self.exit()
    
    def action_request_quit(self) -> None:
        self.push_screen(QuitScreen())
        
    
            
if __name__ == '__main__':
    CONTROL_PORT = "5555"
    OUTPUT_PORT = "5556"
    LOGGING_PORT = "5557" 

    zmq_log_handler = PUBHandler('tcp://*:%s' % LOGGING_PORT)
    logger.addHandler(zmq_log_handler)

    context = zmq.Context()
    socket = context.socket(REP)
    socket.bind("tcp://*:%s" % CONTROL_PORT)
    pubsocket = context.socket(PUB)
    pubsocket.bind("tcp://*:%s" % OUTPUT_PORT)

    async def backend():
        """
        Fake program to be controlled by TUI.
        """
        while True:
            msg = await socket.recv_multipart()
            if msg[0].decode('utf-8') == 'quit':
                await socket.send_string("QUIT")
            else:
                await socket.send_string("Awaiting input:")


    async def publish():
        """
        Set up a fake server to publish messages for testing.
        """
        counter = 0
        while True:
            await pubsocket.send_string("test " + str(counter))
            await asyncio.sleep(1)
            counter += 1
    
    async def main_loop():
        app = TUI(CONTROL_PORT, OUTPUT_PORT, LOGGING_PORT)

        # the following construct ensures both the (infinite) fake servers are killed once the tui finishes
        finished, unfinished = await asyncio.wait([app.run_async(), publish(), backend()], return_when=asyncio.FIRST_COMPLETED)

        for task in unfinished:
            task.cancel()

    asyncio.run(main_loop())