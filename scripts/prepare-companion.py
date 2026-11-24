from pathlib import Path

root = Path(__file__).resolve().parents[1] / ".local/jarvis-work/livekit_flutter_starter-main"


def edit(name, old, new):
    p = root / name
    s = p.read_text(encoding="utf-8")
    assert old in s, (name, old[:100])
    p.write_text(s.replace(old, new), encoding="utf-8")


(root / "lib/companion_mode.dart").write_text(
    "/// S23 FE build: work reports and Projects, without the master/social role.\n"
    "const companionMode = bool.fromEnvironment('JARVIS_COMPANION');\n",
    encoding="utf-8",
)
edit("lib/master/event_store.dart", "static const modeKey", "static const workModeKey = 'jarvis_work_mode';\n  static const modeKey")
edit("lib/master/event_store.dart", "bool get masterMode", "bool get workMode => _prefs.getBool(workModeKey) ?? false;\n  Future<void> setWorkMode(bool value) => _prefs.setBool(workModeKey, value);\n\n  bool get masterMode")
m = "lib/master/master_ctrl.dart"
edit(m, "import 'dart:convert';", "import 'dart:convert';\nimport '../companion_mode.dart';")
edit(m, "bool? serverMaster;", "bool? serverMaster;\n  bool serverWorkAccess = false;")
edit(m, "enabled = store.masterMode;\n    settings = store.settings;", """enabled = companionMode ? true : store.masterMode;
    if (companionMode) {
      await store.setMasterMode(false);
      await store.setWorkMode(true);
    }
    settings = companionMode ? store.settings.copyWith(announceMessages: false, landscape: false) : store.settings;""")
edit(m, "messages = store.messages;", "messages = companionMode ? [] : store.messages;")
edit(m, "await store.setMasterMode(value);", "if (companionMode) {\n      await store.setWorkMode(value);\n    } else {\n      await store.setMasterMode(value);\n    }")
edit(m, "if (serverMaster == true) _startEventStream(api);", "if (serverWorkAccess) _startEventStream(api);")
edit(m, "if (serverMaster != true) {", "serverWorkAccess = profile['work_access'] == true || serverMaster == true;\n      if (!serverWorkAccess) {")
edit(m, "'The server does not treat this phone as the master, so reports are not sent here. '", "'This device needs work access to receive reports and use Projects. '")
edit(m, "sudo jarvis-control master", "sudo jarvis-control work")
edit(m, "Future<bool> _refreshSocialAccess() async {", "Future<bool> _refreshSocialAccess() async {\n    if (companionMode) return false;")
edit(m, "Future<void> _restoreSocial() async {", "Future<void> _restoreSocial() async {\n    if (companionMode) return;")
edit(m, "if (!enabled || _store == null) return false;", "if (companionMode) return true;\n    if (!enabled || _store == null) return false;")
edit(m, "if (batch.isEmpty || !settings.announceMessages", "if (companionMode || batch.isEmpty || !settings.announceMessages")
edit(m, "Future<void> readMessage(SocialMessage message) async {", "Future<void> readMessage(SocialMessage message) async {\n    if (companionMode) return;")
edit(m, "if (!enabled) return {'available': false,", "if (companionMode) return {'available': false, 'reason': 'Social messages are disabled on this companion phone.'};\n    if (!enabled) return {'available': false,")
edit(m, "enabled && settings.landscape", "!companionMode && enabled && settings.landscape")
edit(m, "settings.copyWith(announceMessages: value)", "settings.copyWith(announceMessages: companionMode ? false : value)")
edit(m, "if (store == null || api == null || serverMaster != true)", "if (companionMode || store == null || api == null || serverMaster != true)")
# A report notification uses the same spoken report path as the Reports screen.
edit(m, "  // Life cycle", """  Future<void> openReportNotification(String id) async {
    if (!enabled) return;
    await _store?.reload();
    reports = _store?.events ?? reports;
    final matches = reports.where((event) => event.id == id);
    if (matches.isNotEmpty) await readReport(matches.first);
    notifyListeners();
  }

  // Life cycle""")
edit("lib/controllers/app_ctrl.dart", "if (!payload.startsWith(Alarms.routinePrefix)) return;", """if (payload.startsWith('report:')) {
      unawaited(master.openReportNotification(payload.substring('report:'.length)));
      return;
    }
    if (!payload.startsWith(Alarms.routinePrefix)) return;""")
edit("lib/services/alarms.dart", "if (store.masterMode)", "if (store.masterMode || store.workMode)")
s = "lib/screens/master_screen.dart"
edit(s, "import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport '../companion_mode.dart';")
edit(s, "=> box.maxWidth > box.maxHeight", "=> !companionMode && box.maxWidth > box.maxHeight")
edit(s, "'Master phone'", "companionMode ? 'JARVIS · Companion' : 'Master phone'")
edit(s, "title: const Text('Master phone mode')", "title: const Text(companionMode ? 'Work reports and Projects' : 'Master phone mode')")
edit(s, "subtitle: const Text('Wake word, reports, messages; music only on the computer')", "subtitle: const Text(companionMode ? 'Reports, AI limits and requests on your main PC' : 'Wake word, reports, messages; music only on the computer')")
edit(s, "              _SectionTitle(\n                'Messages',", "              if (!companionMode) ...[\n              _SectionTitle(\n                'Messages',")
edit(s, "...master.messages.take(15).map((m) => _MessageTile(master: master, message: m)),", "...master.messages.take(15).map((m) => _MessageTile(master: master, message: m)),\n              ],")
edit(s, "            SwitchListTile(\n              contentPadding: EdgeInsets.zero,\n              title: const Text('Announce messages')", "            if (!companionMode) SwitchListTile(\n              contentPadding: EdgeInsets.zero,\n              title: const Text('Announce messages')")
edit(s, "TextButton(onPressed: master.openSocialSettings, child: const Text('Notification access'))", "if (!companionMode) TextButton(onPressed: master.openSocialSettings, child: const Text('Notification access'))")
k = "android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/"
edit(k+"MainActivity.kt", '.getBoolean("flutter.jarvis_master_mode", false)', '.getBoolean("flutter.jarvis_master_mode", false) || isWorkMode(context)\n\n        fun isWorkMode(context: Context): Boolean =\n            context.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)\n                .getBoolean("flutter.jarvis_work_mode", false)')
edit(k+"SocialListener.kt", "        val app = APPS[sbn.packageName]", "        if (MainActivity.isWorkMode(this)) return\n        val app = APPS[sbn.packageName]")
# Preserve input after rejection/offline, prevent repeated sends.
p = "lib/screens/projects_screen.dart"
edit(p, "  String _filter = '';", "  String _filter = '';\n  bool _sending = false;")
edit(p, """    if (text.isEmpty) return;
    _text.clear();
    final conv = await widget.projects.send('dicevtt', text, newConversation: true);""", """    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
    final conv = await widget.projects.send('dicevtt', text, newConversation: true);
    _text.clear();""")
edit(p, """      unawaited(widget.projects.refreshList());
    }
  }

  @override
  Widget build""", """      unawaited(widget.projects.refreshList());
    }
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build""")
edit(p, "IconButton(onPressed: _start,", "IconButton(onPressed: _sending ? null : _start,")
edit("pubspec.yaml", "version: 1.4.0+18", "version: 1.5.0+19")
print("Companion changes prepared.")
