import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

class CompetitionsPage extends StatefulWidget {
  const CompetitionsPage({super.key});

  @override
  State<CompetitionsPage> createState() => _CompetitionsPageState();
}

class _CompetitionsPageState extends State<CompetitionsPage> {
  static const _storage = FlutterSecureStorage();
  final _api = ApiClient();
  final _search = TextEditingController();
  final _region = TextEditingController();
  String _selectedSport = '';
  static const _sportOptions = <String>[
    'Жүдо', 'Самбо', 'Чөлөөт бөх', 'Үндэсний бөх', 'Бокс',
    'Волейбол', 'Сагсан бөмбөг', 'Хөл бөмбөг', 'Таеквондо',
    'Каратэ', 'Гимнастик', 'Бусад',
  ];
  List<Map<String, dynamic>> _items = [];
  bool _loading = false;
  String? _error;

  Future<String?> _token() => _storage.read(key: 'arena_access_token');

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _api.close();
    _search.dispose();
    _region.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (!ApiConfig.isConfigured) {
      setState(() {
        _items = [];
        _error = 'Тэмцээний бодит мэдээлэл харахын тулд ARINA_API_BASE_URL серверийн хаягийг тохируулна уу.';
      });
      return;
    }
    final token = await _token();
    if (token == null) {
      setState(() => _error = 'Нэвтрэх эрх олдсонгүй. Дахин нэвтэрнэ үү.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final query = <String, String>{};
      if (_search.text.trim().isNotEmpty) query['search'] = _search.text.trim();
      if (_selectedSport.isNotEmpty) query['sport'] = _selectedSport;
      if (_region.text.trim().isNotEmpty) query['region'] = _region.text.trim();
      final suffix = query.entries
          .map((entry) => '${Uri.encodeQueryComponent(entry.key)}=${Uri.encodeQueryComponent(entry.value)}')
          .join('&');
      final result = await _api.getList('/competitions${suffix.isEmpty ? '' : '?$suffix'}', token: token);
      if (!mounted) return;
      setState(() => _items = result);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _create() async {
    final data = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const _CreateCompetitionDialog(),
    );
    if (data == null) return;
    final token = await _token();
    if (token == null) {
      setState(() => _error = 'Нэвтрэх эрх олдсонгүй.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _api.postAuthorized('/competitions', token: token, body: data);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Тэмцээн амжилттай үүслээ.')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _date(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? '');
    if (parsed == null) return 'Огноо тодорхойгүй';
    return '${parsed.year}-${parsed.month.toString().padLeft(2, '0')}-${parsed.day.toString().padLeft(2, '0')}';
  }

  String _status(String value) {
    const labels = {
      'registration_open': 'Бүртгэл нээлттэй',
      'registration_closed': 'Бүртгэл хаагдсан',
      'in_progress': 'Явагдаж байна',
      'completed': 'Дууссан',
      'cancelled': 'Цуцлагдсан',
    };
    return labels[value] ?? value;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Спортын тэмцээн'),
        actions: [
          IconButton(
            tooltip: 'Шинэчлэх',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _loading ? null : _create,
        icon: const Icon(Icons.add),
        label: const Text('Тэмцээн үүсгэх'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF211052), Color(0xFF4330A8)],
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.emoji_events, color: Colors.white, size: 36),
                  SizedBox(height: 10),
                  Text(
                    'ARINA 360 COMPETITIONS',
                    style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Тэмцээн зохион байгуулж, тамирчдаа бүртгэн, сугалаа болон оноог нэг дор удирдаарай.',
                    style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  children: [
                    DropdownButtonFormField<String>(
                      value: _selectedSport.isEmpty ? null : _selectedSport,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Спортын төрлөө сонгоно уу',
                        prefixIcon: Icon(Icons.sports),
                      ),
                      items: [
                        const DropdownMenuItem<String>(
                          value: '',
                          child: Text('Бүх спортын төрөл'),
                        ),
                        ..._sportOptions.map((sport) => DropdownMenuItem<String>(
                          value: sport,
                          child: Text(sport),
                        )),
                      ],
                      onChanged: (value) {
                        setState(() => _selectedSport = value ?? '');
                        _load();
                      },
                    ),
                    const SizedBox(height: 8),
                    ExpansionTile(
                      tilePadding: EdgeInsets.zero,
                      title: const Text('Нарийвчилсан хайлт'),
                      leading: const Icon(Icons.tune),
                      children: [
                        TextField(
                          controller: _search,
                          textInputAction: TextInputAction.search,
                          onSubmitted: (_) => _load(),
                          decoration: const InputDecoration(
                            labelText: 'Тэмцээний нэр (заавал биш)',
                            prefixIcon: Icon(Icons.search),
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _region,
                          textInputAction: TextInputAction.search,
                          onSubmitted: (_) => _load(),
                          decoration: const InputDecoration(
                            labelText: 'Байршил (заавал биш)',
                            prefixIcon: Icon(Icons.location_on_outlined),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: _loading ? null : _load,
                        icon: const Icon(Icons.filter_alt),
                        label: const Text('ХАЙЛТ ХИЙХ'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null)
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(_error!),
                ),
              ),
            if (!_loading && _items.isEmpty && _error == null)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Text(
                    'Одоогоор тэмцээн бүртгэгдээгүй байна. Эхний тэмцээнээ үүсгээрэй.',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ..._items.map((item) => Card(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(20),
                    onTap: () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => CompetitionDetailPage(tournamentId: item['id'] as int),
                        ),
                      );
                      if (mounted) _load();
                    },
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.emoji_events, color: Color(0xFF7043EA)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  item['title']?.toString() ?? 'Нэргүй тэмцээн',
                                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text('${item['sport']} • ${item['region']}'),
                          Text('${_date(item['starts_at'])} • ${item['venue']}'),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(child: Text('Оролцогч: ${item['participant_count']}/${item['max_participants']}')),
                              Chip(label: Text(_status(item['status']?.toString() ?? ''))),
                            ],
                          ),
                          const Align(
                            alignment: Alignment.centerRight,
                            child: Text('ДЭЛГЭРЭНГҮЙ  →', style: TextStyle(color: Color(0xFF7043EA), fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                    ),
                  ),
                )),
          ],
        ),
      ),
    );
  }
}

class _CreateCompetitionDialog extends StatefulWidget {
  const _CreateCompetitionDialog();

  @override
  State<_CreateCompetitionDialog> createState() => _CreateCompetitionDialogState();
}

class _CreateCompetitionDialogState extends State<_CreateCompetitionDialog> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _sport = TextEditingController(text: 'Жүдо');
  final _region = TextEditingController(text: 'Улаанбаатар');
  final _venue = TextEditingController();
  final _max = TextEditingController(text: '64');
  String _format = 'single_elimination';
  DateTime _startsAt = DateTime.now().add(const Duration(days: 14));

  @override
  void dispose() {
    _title.dispose();
    _sport.dispose();
    _region.dispose();
    _venue.dispose();
    _max.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _startsAt.isAfter(now) ? _startsAt : now.add(const Duration(days: 1)),
      firstDate: now,
      lastDate: now.add(const Duration(days: 1095)),
    );
    if (picked != null) setState(() => _startsAt = DateTime(picked.year, picked.month, picked.day, _startsAt.hour, _startsAt.minute));
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_startsAt));
    if (picked != null) setState(() => _startsAt = DateTime(_startsAt.year, _startsAt.month, _startsAt.day, picked.hour, picked.minute));
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Шинэ тэмцээн үүсгэх'),
      content: SizedBox(
        width: 440,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(controller: _title, decoration: const InputDecoration(labelText: 'Тэмцээний нэр'), validator: (v) => (v ?? '').trim().length < 3 ? '3-аас дээш тэмдэгт оруулна уу' : null),
                const SizedBox(height: 8),
                TextFormField(controller: _sport, decoration: const InputDecoration(labelText: 'Спортын төрөл'), validator: (v) => (v ?? '').trim().isEmpty ? 'Спортын төрөл оруулна уу' : null),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: _format,
                  decoration: const InputDecoration(labelText: 'Тэмцээний формат'),
                  items: const [
                    DropdownMenuItem(value: 'single_elimination', child: Text('Хасагдах шатны сугалаа')),
                    DropdownMenuItem(value: 'round_robin', child: Text('Тойргийн систем')),
                  ],
                  onChanged: (value) => setState(() => _format = value ?? _format),
                ),
                const SizedBox(height: 8),
                TextFormField(controller: _region, decoration: const InputDecoration(labelText: 'Аймаг / хот'), validator: (v) => (v ?? '').trim().isEmpty ? 'Байршил оруулна уу' : null),
                const SizedBox(height: 8),
                TextFormField(controller: _venue, decoration: const InputDecoration(labelText: 'Заал / талбай'), validator: (v) => (v ?? '').trim().isEmpty ? 'Заал эсвэл талбай оруулна уу' : null),
                const SizedBox(height: 8),
                TextFormField(controller: _max, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Оролцогчийн дээд тоо'), validator: (v) { final n = int.tryParse(v ?? ''); return n == null || n < 2 || n > 2048 ? '2–2048 хооронд тоо оруулна уу' : null; }),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: OutlinedButton.icon(onPressed: _pickDate, icon: const Icon(Icons.calendar_month), label: Text('${_startsAt.year}-${_startsAt.month.toString().padLeft(2, '0')}-${_startsAt.day.toString().padLeft(2, '0')}'))),
                    const SizedBox(width: 8),
                    Expanded(child: OutlinedButton.icon(onPressed: _pickTime, icon: const Icon(Icons.schedule), label: Text(TimeOfDay.fromDateTime(_startsAt).format(context)))),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('БОЛИХ')),
        FilledButton(
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.pop(context, {
              'title': _title.text.trim(),
              'sport': _sport.text.trim(),
              'format': _format,
              'region': _region.text.trim(),
              'venue': _venue.text.trim(),
              'starts_at': _startsAt.toUtc().toIso8601String(),
              'max_participants': int.parse(_max.text.trim()),
            });
          },
          child: const Text('ҮҮСГЭХ'),
        ),
      ],
    );
  }
}

class CompetitionDetailPage extends StatefulWidget {
  final int tournamentId;
  const CompetitionDetailPage({super.key, required this.tournamentId});

  @override
  State<CompetitionDetailPage> createState() => _CompetitionDetailPageState();
}

class _CompetitionDetailPageState extends State<CompetitionDetailPage> {
  static const _storage = FlutterSecureStorage();
  final _api = ApiClient();
  Map<String, dynamic>? _tournament;
  List<Map<String, dynamic>> _participants = [];
  List<Map<String, dynamic>> _matches = [];
  bool _loading = false;
  String? _error;

  Future<String?> _token() => _storage.read(key: 'arena_access_token');

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _api.close();
    super.dispose();
  }

  Future<void> _load() async {
    if (!ApiConfig.isConfigured) {
      setState(() => _error = 'Серверийн API хаяг тохируулаагүй байна.');
      return;
    }
    final token = await _token();
    if (token == null) {
      setState(() => _error = 'Нэвтрэх эрх олдсонгүй.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final result = await Future.wait([
        _api.get('/competitions/${widget.tournamentId}', token: token),
        _api.getList('/competitions/${widget.tournamentId}/participants', token: token),
        _api.getList('/competitions/${widget.tournamentId}/matches', token: token),
      ]);
      if (!mounted) return;
      setState(() {
        _tournament = result[0] as Map<String, dynamic>;
        _participants = result[1] as List<Map<String, dynamic>>;
        _matches = result[2] as List<Map<String, dynamic>>;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _register() async {
    final data = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const _RegisterParticipantDialog(),
    );
    if (data == null) return;
    await _mutate('/competitions/${widget.tournamentId}/register', data, 'Оролцогч бүртгэгдлээ.');
  }

  Future<void> _mutate(String path, Map<String, dynamic> body, String success) async {
    final token = await _token();
    if (token == null) {
      setState(() => _error = 'Нэвтрэх эрх олдсонгүй.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      await _api.postAuthorized(path, token: token, body: body);
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(success)));
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _emptyPost(String path, String success) async {
    await _mutate(path, {}, success);
  }

  Future<void> _score(Map<String, dynamic> match) async {
    final first = TextEditingController();
    final second = TextEditingController();
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Оноо бүртгэх • ${match['stage_name']}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(match['participant1_name']?.toString() ?? 'Тамирчин 1'),
            TextField(controller: first, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Оноо')),
            const SizedBox(height: 8),
            Text(match['participant2_name']?.toString() ?? 'Тамирчин 2'),
            TextField(controller: second, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Оноо')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('БОЛИХ')),
          FilledButton(
            onPressed: () {
              final a = int.tryParse(first.text);
              final b = int.tryParse(second.text);
              if (a == null || b == null || a < 0 || b < 0) return;
              Navigator.pop(dialogContext, {'score1': a, 'score2': b});
            },
            child: const Text('ХАДГАЛАХ'),
          ),
        ],
      ),
    );
    first.dispose();
    second.dispose();
    if (result != null) {
      await _mutate('/competitions/${widget.tournamentId}/matches/${match['id']}/score', result, 'Тоглолтын оноо хадгалагдлаа.');
    }
  }

  String _status(String? value) {
    const labels = {
      'registration_open': 'Бүртгэл нээлттэй',
      'registration_closed': 'Бүртгэл хаагдсан',
      'in_progress': 'Явагдаж байна',
      'completed': 'Дууссан',
      'scheduled': 'Тоглоход бэлэн',
      'waiting': 'Хүлээгдэж байна',
      'pending': 'Хүлээгдэж байна',
      'cancelled': 'Цуцлагдсан',
    };
    return labels[value] ?? value ?? '';
  }

  @override
  Widget build(BuildContext context) {
    final item = _tournament;
    return Scaffold(
      appBar: AppBar(
        title: Text(item?['title']?.toString() ?? 'Тэмцээн'),
        actions: [IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh))],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
          children: [
            if (_loading) const LinearProgressIndicator(),
            if (_error != null) Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(_error!))),
            if (item != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(item['sport']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 6),
                      Text('${item['region']} • ${item['venue']}'),
                      Text('Оролцогч: ${item['participant_count']}/${item['max_participants']}'),
                      Text('Төлөв: ${_status(item['status']?.toString())}'),
                      Text('Формат: ${item['format'] == 'round_robin' ? 'Тойргийн систем' : 'Хасагдах шат'}'),
                    ],
                  ),
                ),
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (item['status'] == 'registration_open')
                    FilledButton.icon(onPressed: _loading ? null : _register, icon: const Icon(Icons.person_add), label: const Text('БҮРТГҮҮЛЭХ')),
                  if (item['status'] == 'registration_open')
                    OutlinedButton(onPressed: _loading ? null : () => _emptyPost('/competitions/${widget.tournamentId}/close-registration', 'Бүртгэл хаагдлаа.'), child: const Text('БҮРТГЭЛ ХААХ')),
                  if (_matches.isEmpty && _participants.length >= 2)
                    FilledButton.icon(onPressed: _loading ? null : () => _emptyPost('/competitions/${widget.tournamentId}/draw', 'Сугалаа үүслээ.'), icon: const Icon(Icons.account_tree), label: const Text('СУГАЛАА ҮҮСГЭХ')),
                ],
              ),
              const SizedBox(height: 14),
              const Text('ОРОЛЦОГЧИД', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
              const SizedBox(height: 8),
              if (_participants.isEmpty) const Text('Оролцогч бүртгэгдээгүй байна.'),
              ..._participants.map((p) => ListTile(
                    leading: CircleAvatar(child: Text(p['seed'] != 0 ? '${p['seed']}' : '•')),
                    title: Text(p['full_name']?.toString() ?? ''),
                    subtitle: Text(p['club_name']?.toString() ?? 'Клуб тодорхойгүй'),
                    trailing: Text(p['status']?.toString() ?? ''),
                  )),
              const SizedBox(height: 16),
              const Text('СУГАЛАА, ТОГЛОЛТЫН ДҮН', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
              const SizedBox(height: 8),
              if (_matches.isEmpty) const Text('Сугалаа хараахан үүсээгүй байна.'),
              ..._matches.map((m) => Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(child: Text('${m['stage_name']} • Тоглолт ${m['match_number']}', style: const TextStyle(fontWeight: FontWeight.bold))),
                              Chip(label: Text(_status(m['status']?.toString()))),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text('${m['participant1_name'] ?? 'Тодорхойгүй'}  ${m['score1'] ?? '-'} : ${m['score2'] ?? '-'}  ${m['participant2_name'] ?? 'Тодорхойгүй'}'),
                          if (m['status'] == 'scheduled')
                            Align(
                              alignment: Alignment.centerRight,
                              child: TextButton.icon(
                                onPressed: _loading ? null : () => _score(m),
                                icon: const Icon(Icons.edit_note),
                                label: const Text('ОНОО БҮРТГЭХ'),
                              ),
                            ),
                        ],
                      ),
                    ),
                  )),
            ],
          ],
        ),
      ),
    );
  }
}

class _RegisterParticipantDialog extends StatefulWidget {
  const _RegisterParticipantDialog();

  @override
  State<_RegisterParticipantDialog> createState() => _RegisterParticipantDialogState();
}

class _RegisterParticipantDialogState extends State<_RegisterParticipantDialog> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _club = TextEditingController();
  final _phone = TextEditingController();
  final _seed = TextEditingController(text: '0');

  @override
  void dispose() {
    _name.dispose();
    _club.dispose();
    _phone.dispose();
    _seed.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Тамирчин бүртгүүлэх'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(controller: _name, decoration: const InputDecoration(labelText: 'Овог нэр'), validator: (v) => (v ?? '').trim().length < 2 ? 'Нэр оруулна уу' : null),
              const SizedBox(height: 8),
              TextFormField(controller: _club, decoration: const InputDecoration(labelText: 'Клуб (заавал биш)')),
              const SizedBox(height: 8),
              TextFormField(controller: _phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Холбоо барих утас'), validator: (v) => (v ?? '').trim().length < 8 ? 'Утасны дугаар оруулна уу' : null),
              const SizedBox(height: 8),
              TextFormField(controller: _seed, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Суулгалтын эрэмбэ (0 = автоматаар)'), validator: (v) => int.tryParse(v ?? '') == null || int.parse(v!) < 0 ? 'Зөв тоо оруулна уу' : null),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('БОЛИХ')),
        FilledButton(
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.pop(context, {
              'full_name': _name.text.trim(),
              'club_name': _club.text.trim().isEmpty ? null : _club.text.trim(),
              'contact_phone': _phone.text.trim(),
              'seed': int.parse(_seed.text.trim()),
            });
          },
          child: const Text('БҮРТГҮҮЛЭХ'),
        ),
      ],
    );
  }
}
