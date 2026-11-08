"""Persistent keyboard shortcuts for File, Edit and Tool menu actions."""
import json

from PySide6.QtGui import QKeySequence

from libs.settings_manager import settings

PORTABLE = QKeySequence.PortableText
# Stable identifiers stay independent of translated action labels.
SHORTCUT_ACTIONS = (
    ('_act_open', 'menu_file', 'menu_open_folder', [QKeySequence.Open]),
    ('_act_save', 'menu_file', 'ldl_save', [QKeySequence.Save]),
    ('_act_settings', 'menu_file', 'menu_preferences', [QKeySequence.Preferences]),
    ('_act_quit', 'menu_file', 'menu_quit', [QKeySequence.Quit]),
    ('_act_clear_recent', 'menu_file', 'recent_clear', []),
    ('act_undo', 'menu_edit', 'ldl_undo', [QKeySequence.Undo]),
    ('act_redo', 'menu_edit', 'ldl_redo', [QKeySequence.Redo]),
    ('_act_history_action', 'menu_edit', 'menu_history', []),
    ('act_select_all', 'menu_edit', 'ldl_select_all', [QKeySequence.SelectAll]),
    ('act_deselect_all', 'menu_edit', 'ldl_deselect_all', ['Ctrl+D']),
    ('act_invert_selection', 'menu_edit', 'ldl_invert_selection', ['Ctrl+I']),
    ('_act_rm_dup', 'menu_tool', 'menu_remove_dup', ['Ctrl+E', 'F5']),
    ('act_nuke_selection', 'menu_tool', 'menu_nuke_selection', []),
    ('_act_sort', 'menu_tool', 'menu_sort_tags', ['Ctrl+R', 'F6']),
    ('_act_underscore_swap', 'menu_tool', 'menu_underscore_swap', ['Ctrl+Shift+U']),
    ('_act_waifu', 'menu_tool', 'menu_waifu_tagger', ['Ctrl+T', 'F8']),
    ('_act_calc_dataset', 'menu_tool', 'menu_calc_dataset', ['Ctrl+Shift+D', 'F9']),
)


class ShortcutManager:
    def __init__(self, window=None):
        self.window = window
        self.defaults = {
            name: [QKeySequence(key).toString(PORTABLE) for key in keys
                   if not QKeySequence(key).isEmpty()]
            for name, _, _, keys in SHORTCUT_ACTIONS
        }
        self.bindings = {name: list(keys) for name, keys in self.defaults.items()}
        try:
            saved = json.loads(settings.value('keyboard_shortcuts', '{}'))
            if isinstance(saved, dict):
                for name, keys in saved.items():
                    if name in self.bindings and isinstance(keys, list) and len(keys) <= 2:
                        if all(isinstance(key, str) and not QKeySequence(key, PORTABLE).isEmpty() for key in keys):
                            self.bindings[name] = [QKeySequence(key, PORTABLE).toString(PORTABLE) for key in keys]
            if self.conflict(self.bindings):
                self.bindings = {name: list(keys) for name, keys in self.defaults.items()}
        except (TypeError, ValueError):
            pass
        self.apply()

    @staticmethod
    def conflict(bindings):
        seen = []
        for name, keys in bindings.items():
            for key in keys:
                sequence = QKeySequence(key, PORTABLE)
                if sequence.isEmpty():
                    continue
                for previous_name, previous in seen:
                    if (sequence.matches(previous) != QKeySequence.NoMatch
                            or previous.matches(sequence) != QKeySequence.NoMatch):
                        return previous_name, name
                seen.append((name, sequence))
        return None

    def apply(self):
        if self.window is not None:
            for name, keys in self.bindings.items():
                getattr(self.window, name).setShortcuts([QKeySequence(key, PORTABLE) for key in keys])

    def save(self, bindings, backend=None):
        if self.conflict(bindings):
            raise ValueError('Conflicting keyboard shortcuts')
        self.bindings = {name: list(bindings[name]) for name in self.defaults}
        (backend if backend is not None else settings).set_value('keyboard_shortcuts', json.dumps(self.bindings))
        self.apply()
