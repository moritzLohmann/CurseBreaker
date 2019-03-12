import os
import sys
import time
import msvcrt
import shutil
import requests
import traceback
from tqdm import tqdm
from colorama import init, Fore
from terminaltables import SingleTable
from prompt_toolkit import PromptSession, HTML, print_formatted_text as printft
from prompt_toolkit.completion import WordCompleter
from distutils.version import StrictVersion
from CB import __version__
from CB.Core import Core


class TUI:
    def __init__(self):
        self.core = Core()
        self.session = PromptSession()
        self.table_data = None
        self.table = None
        self.completer = None
        sys.tracebacklimit = 0
        init()

    def start(self):
        self.print_header()
        # Check if executable is in good location
        if not os.path.isfile('Wow.exe') or not os.path.isdir('Interface\\AddOns') or not os.path.isdir('WTF'):
            printft(HTML('<ansibrightred>This executable should be placed in the same directory where Wow.exe is locate'
                         'd.</ansibrightred>\n'))
            os.system('pause')
            sys.exit(1)
        # Check if client have write access
        try:
            with open('PermissionTest', 'w') as _:
                pass
            os.remove('PermissionTest')
        except IOError:
            printft(HTML('<ansibrightred>CurseBreaker doesn\'t have write rights for the current directory.\n'
                         'Try starting it with administrative privileges.</ansibrightred>\n'))
            os.system('pause')
            sys.exit(1)
        self.auto_update()
        self.core.init_config()
        self.setup_completer()
        # Curse URI Support
        if len(sys.argv) == 2 and 'curse://' in sys.argv[1]:
            try:
                self.c_install(sys.argv[1].strip())
            except Exception as e:
                self.handle_exception(e)
            printft('')
            os.system('pause')
            sys.exit(0)
        # Addons auto update
        if len(self.core.config['Addons']) > 0:
            printft('Automatic update of all addons will start in 5 seconds.\n'
                    'Press any button to enter interactive mode.')
            starttime = time.time()
            keypress = None
            while True:
                if msvcrt.kbhit():
                    keypress = msvcrt.getch()
                    break
                elif time.time() - starttime > 5:
                    break
            if not keypress:
                self.print_header()
                try:
                    self.c_update(False, True)
                except Exception as e:
                    if len(self.table_data) > 1:
                        print('\n' + self.table.table)
                    self.handle_exception(e)
                try:
                    if self.core.backup_check():
                        printft(HTML('\n<ansigreen>Backing up WTF directory:</ansigreen>'))
                        self.core.backup_wtf()
                except Exception as e:
                    self.handle_exception(e)
                printft('')
                os.system('pause')
                sys.exit(0)
        self.print_header()
        printft('Press TAB to see a list of available commands.\nPress CTRL+D to close the application.\n')
        # Prompt session
        while True:
            try:
                command = self.session.prompt(HTML('<ansibrightgreen>CB></ansibrightgreen> '), completer=self.completer)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            else:
                command = command.split(' ', 1)
                if getattr(self, f'c_{command[0].lower()}', False):
                    try:
                        getattr(self, f'c_{command[0].lower()}')(command[1].strip() if len(command) > 1 else False)
                        self.setup_completer()
                    except Exception as e:
                        self.handle_exception(e)
                else:
                    printft('Command not found.')

    def auto_update(self):
        if getattr(sys, 'frozen', False):
            try:
                payload = requests.get('https://api.github.com/repos/AcidWeb/CurseBreaker/releases/latest').json()
                remoteversion = payload['name']
                url = payload['assets'][0]['browser_download_url']
                if StrictVersion(remoteversion[1:]) > StrictVersion(__version__):
                    printft(HTML('<ansigreen>Updating CurseBreaker...</ansigreen>'))
                    if os.path.isfile(sys.executable + '.old'):
                        os.remove(sys.executable + '.old')
                    shutil.move(sys.executable, sys.executable + '.old')
                    payload = requests.get(url)
                    with open(sys.executable, 'wb') as f:
                        f.write(payload.content)
                    printft(HTML('\n<ansibrightgreen>Update complete! Please restart the application.'
                                 '</ansibrightgreen>\n'))
                    os.system('pause')
                    sys.exit(0)
            except Exception as e:
                printft(HTML(f'<ansibrightred>Update failed!\n\nReason: {str(e)}</ansibrightred>\n'))
                os.system('pause')
                sys.exit(1)

    def handle_exception(self, e):
        if getattr(sys, 'frozen', False):
            printft(HTML(f'\n<ansibrightred>{str(e)}</ansibrightred>'))
        else:
            sys.tracebacklimit = 1000
            traceback.print_exc()

    def print_header(self):
        os.system('cls')
        printft(HTML(f'<ansibrightblack>~~~ <ansibrightgreen>CurseBreaker</ansibrightgreen> <ansibrightred>v'
                     f'{__version__}</ansibrightred> ~~~</ansibrightblack>\n'))

    def setup_completer(self):
        commands = ['install', 'uninstall', 'update', 'status', 'orphans', 'toggle_backup', 'uri_integration', 'exit']
        addons = sorted(self.core.config['Addons'], key=lambda k: k['Name'].lower())
        for addon in addons:
            commands.extend([f'uninstall {addon["Name"]}', f'update {addon["Name"]}', f'status {addon["Name"]}'])
        self.completer = WordCompleter(commands, ignore_case=True, sentence=True)

    def setup_table(self):
        self.table_data = [[f'{Fore.LIGHTWHITE_EX}Status{Fore.RESET}', f'{Fore.LIGHTWHITE_EX}Name{Fore.RESET}',
                            f'{Fore.LIGHTWHITE_EX}Version{Fore.RESET}']]
        self.table = SingleTable(self.table_data)
        self.table.justify_columns[0] = 'center'

    def c_install(self, args):
        if args:
            addons = args.split(',')
            self.setup_table()
            with tqdm(total=len(addons), bar_format='{n_fmt}/{total_fmt} |{bar}|') as pbar:
                for addon in addons:
                    installed, name, version = self.core.add_addon(addon)
                    if installed:
                        self.table_data.append([f'{Fore.GREEN}Installed{Fore.RESET}', name, version])
                    else:
                        self.table_data.append([f'{Fore.LIGHTBLACK_EX}Already installed{Fore.RESET}', name, version])
                    pbar.update(1)
            print(self.table.table)
        else:
            printft(HTML('<ansigreen>Usage:</ansigreen>\n\tThis command accepts a comma-separated list of links as an a'
                         'rgument.\n<ansigreen>Supported URLs:</ansigreen>\n\thttps://www.curseforge.com/wow/addons/[ad'
                         'don_name]\n\thttps://www.wowinterface.com/downloads/[addon_name]\n\tElvUI\n\tElvUI:Dev'))

    def c_uninstall(self, args):
        if args:
            addons = args.split(',')
            self.setup_table()
            with tqdm(total=len(addons), bar_format='{n_fmt}/{total_fmt} |{bar}|') as pbar:
                for addon in addons:
                    name, version = self.core.del_addon(addon)
                    if name:
                        self.table_data.append([f'{Fore.RED}Uninstalled{Fore.RESET}', name, version])
                    else:
                        self.table_data.append([f'{Fore.LIGHTBLACK_EX}Not installed{Fore.RESET}', addon, ''])
                    pbar.update(1)
            print(self.table.table)
        else:
            printft(HTML('<ansigreen>Usage:</ansigreen>\n\tThis command accepts a comma-separated list of links or addo'
                         'n names as an argument.\n<ansigreen>Supported URLs:</ansigreen>\n\thttps://www.curseforge.com'
                         '/wow/addons/[addon_name]\n\thttps://www.wowinterface.com/downloads/[addon_name]\n\tElvUI\n\tE'
                         'lvUI:Dev'))

    def c_update(self, args, addline=False, update=True):
        if args:
            addons = args.split(',')
        else:
            addons = sorted(self.core.config['Addons'], key=lambda k: k['Name'].lower())
        self.setup_table()
        with tqdm(total=len(addons), bar_format='{n_fmt}/{total_fmt} |{bar}|') as pbar:
            for addon in addons:
                name, versionnew, versionold = self.core.\
                    update_addon(addon if isinstance(addon, str) else addon['URL'], update)
                if versionold:
                    if versionold == versionnew:
                        self.table_data.append([f'{Fore.GREEN}Up-to-date{Fore.RESET}', name, versionold])
                    else:
                        self.table_data.append([f'{Fore.YELLOW}{"Updated" if update else "Update available"}'
                                                f'{Fore.RESET}', name, f'{versionold} {Fore.LIGHTBLACK_EX}>>'
                                                f'>{Fore.RESET} {versionnew}'])
                else:
                    self.table_data.append([f'{Fore.LIGHTBLACK_EX}Not installed{Fore.RESET}', addon, ''])
                pbar.update(1)
        print('\n' + self.table.table if addline else self.table.table)

    def c_status(self, args):
        self.c_update(args, False, False)

    def c_orphans(self, _):
        orphans = self.core.find_orphans()
        printft(HTML('<ansigreen>Directories that are not part of any installed addon:</ansigreen>'))
        for orphan in sorted(orphans):
            printft(orphan)

    def c_uri_integration(self, _):
        self.core.create_reg()
        printft('CurseBreaker.reg file was created. Import it to enable integration.')

    def c_toggle_backup(self, _):
        status = self.core.backup_toggle()
        printft('Backup of WTF directory is now:',
                HTML('<ansigreen>ENABLED</ansigreen>') if status else HTML('<ansired>DISABLED</ansired>'))

    def c_exit(self, _):
        sys.exit(0)


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
    os.system(f'title CurseBreaker v{__version__}')
    os.system('mode con: cols=100 lines=50')
    app = TUI()
    app.start()


