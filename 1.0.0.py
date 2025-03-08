import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
import os
import time
from tkinter.font import Font

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    class TkinterDnD:
        pass


    DND_FILES = None

SYNTAX_RULES = {
    'python': {
        'keywords': r'\b(if|else|for|while|def|class|import|from|try|except|finally|return|break|continue)\b',
        'patterns': [
            (r'#.*?$', 'comment', re.MULTILINE),
            (r'""".*?"""', 'string', re.DOTALL),
            (r"'''.*?'''", 'string', re.DOTALL),
            (r'"(?:[^"\\]|\\.)*"', 'string'),
            (r"'(?:[^'\\]|\\.)*'", 'string'),
            (r'\b\d+\.?\d*\b', 'number'),
            (r'\b(True|False|None)\b', 'constant')
        ]
    },
    'html': {
        'patterns': [
            (r'<!--.*?-->', 'comment', re.DOTALL),
            (r'<\w+>', 'tag'),
            (r'</\w+>', 'tag'),
            (r'".*?"', 'string'),
            (r"'.*?'", 'string'),
            (r'&\w+;', 'entity')
        ]
    }
}

THEMES = {
    'light': {
        'bg': '#ffffff', 'fg': '#000000',
        'line_bg': '#f0f0f0', 'insert': '#000000',
        'select_bg': '#c0c0c0', 'select_fg': '#000000'
    },
    'dark': {
        'bg': '#2d2d2d', 'fg': '#e0e0e0',
        'line_bg': '#404040', 'insert': '#ffffff',
        'select_bg': '#505050', 'select_fg': '#ffffff'
    }
}


class LineNumberCanvas(tk.Canvas):
    def __init__(self, parent, text_widget, **kwargs):
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget  # 添加关联的文本组件
        self.font = Font(family='Consolas', size=12)
        self.bind('<Configure>', self._update)
        self.text_widget.bind('<KeyRelease>', self._update)
        self.text_widget.bind('<MouseWheel>', self._update)

    def _update(self, event=None):
        self.delete('all')
        width = self.winfo_width()
        lines = self.text_widget.get('1.0', 'end-1c').split('\n')

        for i in range(len(lines)):
            y_pos = self.text_widget.bbox(f'{i + 1}.0')[1]
            self.create_text(
                width - 5, y_pos,
                text=str(i + 1),
                anchor='ne',
                font=self.font,
                fill=THEMES['light' if self['bg'] == '#f0f0f0' else 'dark']['fg']
            )


class SyntaxHighlighter:
    def __init__(self, text_widget):
        self.text = text_widget
        self.language = 'python'
        self._init_tags()

    def _init_tags(self):
        tag_colors = {
            'keyword': 'blue',
            'string': 'green',
            'comment': 'gray',
            'number': 'purple',
            'constant': 'orange',
            'tag': 'blue',
            'entity': 'red'
        }
        for name, color in tag_colors.items():
            self.text.tag_configure(name, foreground=color)

    def set_language(self, language):
        self.language = language
        self.highlight()

    def highlight(self, event=None):
        self._clear_tags()
        if self.language in SYNTAX_RULES:
            rules = SYNTAX_RULES[self.language]
            if 'keywords' in rules:
                self._highlight_pattern(rules['keywords'], 'keyword')
            for pattern in rules.get('patterns', []):
                self._highlight_pattern(*pattern)

    def _highlight_pattern(self, pattern, tag, flags=0):
        start = '1.0'
        while True:
            start = self.text.search(pattern, start, stopindex='end',
                                     regexp=True, count=tk.ANCHOR, flags=flags)
            if not start:
                break
            end = f"{start}+{self.text.count('chars', start, tk.ANCHOR)[0]}c"
            self.text.tag_add(tag, start, end)
            start = end

    def _clear_tags(self):
        for tag in ['keyword', 'string', 'comment', 'number', 'constant', 'tag', 'entity']:
            self.text.tag_remove(tag, '1.0', 'end')


class EditorTab(ttk.Frame):
    def __init__(self, master, editor):
        super().__init__(master)
        self.editor = editor
        self.file_path = None
        self.encoding = 'utf-8'
        self.text_modified = False
        self.last_save = time.time()

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True)

        # 先创建文本组件
        self.text = scrolledtext.ScrolledText(
            main_frame,
            wrap='word',
            font=('Consolas', 12),
            undo=True,
            padx=5,
            pady=5
        )
        self.text.pack(side='right', fill='both', expand=True)

        # 再创建行号组件并关联文本组件
        self.line_numbers = LineNumberCanvas(
            main_frame,
            self.text,  # 正确传递text_widget参数
            width=60,
            bg=THEMES[self.editor.theme]['line_bg']
        )
        self.line_numbers.pack(side='left', fill='y')

        self.highlighter = SyntaxHighlighter(self.text)
        self._apply_theme()

    def _bind_events(self):
        self.text.bind('<<Modified>>', self._on_modify)
        self.text.bind('<KeyRelease>', self._auto_save_check)

    def _on_modify(self, event):
        if self.text.edit_modified():
            self.text_modified = True
            self.editor.update_status()
            self.text.edit_modified(False)
            self.highlighter.highlight()

    def _auto_save_check(self, event):
        if self.editor.auto_save and time.time() - self.last_save > 30:
            self.save()

    def save(self):
        if self.file_path:
            try:
                content = self.text.get('1.0', 'end-1c')
                with open(self.file_path, 'w', encoding=self.encoding) as f:
                    f.write(content)
                self.text_modified = False
                self.last_save = time.time()
                self.editor.update_status()
            except Exception as e:
                messagebox.showerror('保存错误', f'无法保存文件：{str(e)}')

    def _apply_theme(self):
        theme = THEMES[self.editor.theme]
        self.text.configure(
            bg=theme['bg'],
            fg=theme['fg'],
            insertbackground=theme['insert'],
            selectbackground=theme['select_bg'],
            selectforeground=theme['select_fg']
        )
        self.line_numbers.configure(bg=theme['line_bg'])


class TextEditor(TkinterDnD.Tk if DND_FILES else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('文本编辑器')
        self.theme = ('dark')
        self.auto_save = False
        self._current_language = 'python'

        self._setup_ui()
        self._setup_dnd()
        self._apply_theme()

    def _setup_ui(self):
        self._create_widgets()
        self._setup_menu()
        self._setup_tab_menu()
        self.add_tab('新文件')

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        self.status_bar = ttk.Label(self, text='就绪', relief='sunken')
        self.status_bar.pack(side='bottom', fill='x')

        self.notebook.bind('<<NotebookTabChanged>>', lambda e: self.update_status())

    def _setup_menu(self):
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label='新建', command=lambda: self.add_tab(), accelerator='Ctrl+N')
        file_menu.add_command(label='打开', command=self.open_file, accelerator='Ctrl+O')
        file_menu.add_command(label='保存', command=self.save_file, accelerator='Ctrl+S')
        file_menu.add_checkbutton(label='自动保存', command=self.toggle_auto_save)
        file_menu.add_separator()
        file_menu.add_command(label='退出', command=self.quit)
        menu_bar.add_cascade(label='文件', menu=file_menu)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label='切换主题', command=self.toggle_theme)
        view_menu.add_command(label='放大字体', command=lambda: self.zoom_font(1))
        view_menu.add_command(label='缩小字体', command=lambda: self.zoom_font(-1))
        menu_bar.add_cascade(label='视图', menu=view_menu)

        lang_menu = tk.Menu(menu_bar, tearoff=0)
        for lang in SYNTAX_RULES.keys():
            lang_menu.add_command(
                label=lang.capitalize(),
                command=lambda l=lang: self.set_language(l)
            )
        menu_bar.add_cascade(label='语言', menu=lang_menu)

        self.config(menu=menu_bar)

        self.bind_all('<Control-n>', lambda e: self.add_tab())
        self.bind_all('<Control-o>', lambda e: self.open_file())
        self.bind_all('<Control-s>', lambda e: self.save_file())

    def _setup_tab_menu(self):
        self.tab_menu = tk.Menu(self, tearoff=0)
        self.tab_menu.add_command(label='关闭标签页', command=self.close_tab)
        self.tab_menu.add_command(label='关闭其他标签页', command=self.close_other_tabs)

        self.notebook.bind('<Button-3>', self._show_tab_menu)

    def _show_tab_menu(self, event):
        try:
            index = self.notebook.index(f'@{event.x},{event.y}')
            self.notebook.select(index)
            self.tab_menu.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            pass

    def _setup_dnd(self):
        if DND_FILES:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._handle_drop)

    def _handle_drop(self, event):
        files = event.data.split()
        for path in files:
            if os.path.isfile(path):
                self.open_file(path)

    def add_tab(self, title='新文件', content='', path=None):
        tab = EditorTab(self.notebook, self)
        self.notebook.add(tab, text=title)
        if content:
            tab.text.insert('end', content)
        if path:
            tab.file_path = path
            self._detect_language(path)
        self.notebook.select(tab)

    def _detect_language(self, path):
        ext = os.path.splitext(path)[1].lower()
        lang_map = {
            '.py': 'python',
            '.html': 'html',
            '.js': 'javascript'
        }
        self.set_language(lang_map.get(ext, 'text'))

    def set_language(self, lang):
        self._current_language = lang
        current_tab = self.current_tab()
        if current_tab:
            current_tab.highlighter.set_language(lang)

    def current_tab(self):
        return self.notebook.nametowidget(self.notebook.select()) if self.notebook.tabs() else None

    def open_file(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[
                ('文本文件', '*.txt'),
                ('Python文件', '*.py'),
                ('HTML文件', '*.html'),
                ('所有文件', '*.*')
            ])

        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                title = os.path.basename(path)
                self.add_tab(title, content, path)
                self._detect_language(path)
            except Exception as e:
                messagebox.showerror('打开错误', f'无法打开文件：{str(e)}')

    def save_file(self):
        tab = self.current_tab()
        if tab:
            if tab.file_path:
                tab.save()
            else:
                self.save_as()

    def save_as(self):
        tab = self.current_tab()
        if tab:
            path = filedialog.asksaveasfilename(
                defaultextension='.txt',
                filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')]
            )
            if path:
                tab.file_path = path
                self.notebook.tab(tab, text=os.path.basename(path))
                tab.save()

    def close_tab(self):
        current = self.current_tab()
        if current:
            if current.text_modified:
                if not self._confirm_save(current):
                    return
            self.notebook.forget(current)

    def close_other_tabs(self):
        current = self.current_tab()
        for tab in self.notebook.tabs():
            if tab != current.winfo_id():
                self.notebook.forget(tab)

    def _confirm_save(self, tab):
        resp = messagebox.askyesnocancel(
            '保存确认',
            '当前文件已修改，是否保存更改？'
        )
        if resp is None:
            return False
        if resp:
            tab.save()
        return True

    def toggle_auto_save(self):
        self.auto_save = not self.auto_save

    def toggle_theme(self):
        self.theme = 'dark' if self.theme == 'light' else 'light'
        self._apply_theme()

    def _apply_theme(self):
        theme = THEMES[self.theme]
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.',
                        background=theme['bg'],
                        foreground=theme['fg'],
                        fieldbackground=theme['bg'],
                        selectbackground=theme['select_bg'],
                        selectforeground=theme['select_fg']
                        )

        for tab in self.notebook.tabs():
            editor_tab = self.notebook.nametowidget(tab)
            editor_tab._apply_theme()

    def zoom_font(self, delta):
        for tab in self.notebook.tabs():
            editor_tab = self.notebook.nametowidget(tab)
            current_font = Font(font=editor_tab.text['font'])
            new_size = max(8, current_font.actual()['size'] + delta)
            editor_tab.text.configure(font=(current_font.actual()['family'], new_size))
            editor_tab.line_numbers.font.configure(size=new_size)

    def update_status(self):
        tab = self.current_tab()
        if tab:
            status = []
            status.append(f"文件：{tab.file_path or '未保存'}")
            status.append(f"编码：{tab.encoding}")
            status.append(f"语言：{self._current_language}")
            status.append(f"状态：{'已修改' if tab.text_modified else '已保存'}")
            self.status_bar.config(text=' | '.join(status))
        else:
            self.status_bar.config(text='就绪')


app = TextEditor()
app.geometry('1200x800')
app.mainloop()
