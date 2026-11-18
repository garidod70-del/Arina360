import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/config/api_config.dart';
import '../../core/network/api_client.dart';

class ApiRefereeBookingPage extends StatefulWidget {
  const ApiRefereeBookingPage({super.key});

  @override
  State<ApiRefereeBookingPage> createState() => _ApiRefereeBookingPageState();
}

class _ApiRefereeBookingPageState extends State<ApiRefereeBookingPage> {
  static const _storage = FlutterSecureStorage();
  final _api = ApiClient();
  final _venue = TextEditingController();
  final _contactName = TextEditingController();
  final _contactPhone = TextEditingController();
  final _fee = TextEditingController(text: '50000');
  final _count = TextEditingController(text: '1');
  final _notes = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  final _sports = const ['Жүдо', 'Чөлөөт бөх', 'Сагсан бөмбөг', 'Волейбол', 'Хөлбөмбөг', 'Үндэсний бөх', 'Шагайн харваа'];
  String _sport = 'Жүдо';
  String _rank = 'Улсын';
  DateTime _eventAt = DateTime.now().add(const Duration(days: 7));
  bool _busy = false;
  String? _error;
  List<Map<String, dynamic>> _requests = [];
  List<Map<String, dynamic>> _referees = [];
  int? _selectedRefereeId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _api.close();
    _venue.dispose();
    _contactName.dispose();
    _contactPhone.dispose();
    _fee.dispose();
    _count.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<String?> _token() => _storage.read(key: 'arena_access_token');

  Future<void> _load() async {
    if (!ApiConfig.isConfigured) {
      setState(() => _error = 'Шүүгчийн бодит захиалга ашиглахын тулд серверийн API хаягийг тохируулах шаардлагатай.');
      return;
    }
    setState(() { _busy = true; _error = null; });
    try {
      final token = await _token();
      if (token == null) throw const ApiException(401, 'Дахин нэвтэрнэ үү.');
      final results = await Future.wait([
        _api.getList('/referees/requests/me', token: token),
        _api.getList('/referees', token: token),
      ]);
      final profile = await _api.get('/profile/me', token: token);
      if (!mounted) return;
      if (_contactName.text.isEmpty) {
        _contactName.text = profile['full_name']?.toString() ?? profile['name']?.toString() ?? '';
      }
      if (_contactPhone.text.isEmpty) {
        _contactPhone.text = profile['phone']?.toString() ?? '';
      }
      final savedSport = profile['sport']?.toString();
      if (_sports.contains(savedSport)) _sport = savedSport!;
      setState(() {
        _requests = results[0];
        _referees = results[1];
        if (_selectedRefereeId == null && _referees.isNotEmpty) _selectedRefereeId = _referees.first['user_id'] as int;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _createRequest() async {
    if (!_formKey.currentState!.validate()) return;
    final token = await _token();
    if (token == null) {
      setState(() => _error = 'Нэвтрэх эрх олдсонгүй. Дахин нэвтэрнэ үү.');
      return;
    }
    setState(() { _busy = true; _error = null; });
    try {
      await _api.postAuthorized('/referees/requests', token: token, body: {
        'sport': _sport,
        'rank': _rank,
        'booking_type': 'Нэг шүүгч',
        'event_at': _eventAt.toUtc().toIso8601String(),
        'venue': _venue.text.trim(),
        'referee_count': int.parse(_count.text),
        'payment_type': 'Нэг тоглолтоор',
        'unit_fee': int.parse(_fee.text),
        'work_days': 1,
        'transport_fee': 0,
        'food_fee': 0,
        'contact_name': _contactName.text.trim(),
        'contact_phone': _contactPhone.text.trim(),
        'notes': _notes.text.trim().isEmpty ? null : _notes.text.trim(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Шүүгчийн захиалга серверт бүртгэгдлээ.')));
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _action(int id, String action, {Map<String, dynamic>? body, String? sport}) async {
    final token = await _token();
    if (token == null) return;
    setState(() { _busy = true; _error = null; });
    try {
      if (action == 'assign') {
        final matches = _referees.where((r) => r['user_id'] == _selectedRefereeId && r['sport'].toString().toLowerCase() == (sport ?? _sport).toLowerCase()).toList();
        final referee = matches.isEmpty ? null : matches.first;
        if (referee == null) throw const ApiException(404, 'Сонгосон спортын баталгаажсан шүүгч олдсонгүй.');
        await _api.postAuthorized('/referees/requests/$id/assign?referee_user_id=${referee['user_id']}', token: token, body: {});
      } else {
        await _api.postAuthorized('/referees/requests/$id/$action', token: token, body: body ?? {});
      }
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _rate(int id) async {
    int score = 5;
    final comment = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(builder: (context, setDialog) => AlertDialog(
        title: const Text('Шүүгчид үнэлгээ өгөх'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButtonFormField<int>(
            value: score,
            decoration: const InputDecoration(labelText: 'Үнэлгээ (1–5)'),
            items: [1,2,3,4,5].map((v) => DropdownMenuItem(value: v, child: Text('$v од'))).toList(),
            onChanged: (v) => setDialog(() => score = v ?? 5),
          ),
          TextField(controller: comment, maxLines: 3, decoration: const InputDecoration(labelText: 'Сэтгэгдэл (заавал биш)')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Болих')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Илгээх')),
        ],
      )),
    );
    if (confirmed == true) await _action(id, 'rating', body: {'score': score, 'comment': comment.text.trim().isEmpty ? null : comment.text.trim()});
    comment.dispose();
  }

  Widget _field(String label, TextEditingController controller, {bool number = false, int maxLines = 1}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextFormField(
        controller: controller,
        keyboardType: number ? TextInputType.number : TextInputType.text,
        maxLines: maxLines,
        decoration: InputDecoration(labelText: label),
        validator: (v) {
          if ((v ?? '').trim().isEmpty) return 'Энэ талбарыг бөглөнө үү';
          if (number && int.tryParse(v!.trim()) == null) return 'Бүхэл тоо оруулна уу';
          if (number && int.parse(v!.trim()) < 0) return 'Эерэг дүн оруулна уу';
          return null;
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Шүүгчийн үйлчилгээ'), actions: [
        IconButton(onPressed: _busy ? null : _load, icon: const Icon(Icons.refresh)),
      ]),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Card(child: Padding(
            padding: const EdgeInsets.all(16),
            child: Form(key: _formKey, child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Шүүгч захиалах', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _sport, decoration: const InputDecoration(labelText: 'Спортын төрөл'),
                items: _sports.map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
                onChanged: (v) => setState(() => _sport = v ?? _sport),
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                value: _rank, decoration: const InputDecoration(labelText: 'Шүүгчийн зэрэглэл'),
                items: ['Олон улсын','Улсын','I зэрэг','II зэрэг','III зэрэг'].map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
                onChanged: (v) => setState(() => _rank = v ?? _rank),
              ),
              const SizedBox(height: 10),
              if (_referees.isNotEmpty) DropdownButtonFormField<int>(
                value: _referees.any((r) => r['user_id'] == _selectedRefereeId) ? _selectedRefereeId : null,
                decoration: const InputDecoration(labelText: 'Баталгаажсан шүүгч (томилгоонд)'),
                items: _referees.map((r) => DropdownMenuItem<int>(value: r['user_id'] as int, child: Text('${r['full_name'] ?? r['sport']} • ${r['rank']}'))).toList(),
                onChanged: (v) => setState(() => _selectedRefereeId = v),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () async {
                  final picked = await showDatePicker(context: context, initialDate: _eventAt, firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 1095)));
                  if (picked != null) setState(() => _eventAt = DateTime(picked.year, picked.month, picked.day, _eventAt.hour, _eventAt.minute));
                },
                icon: const Icon(Icons.calendar_month), label: Text('Огноо: ${_eventAt.year}-${_eventAt.month.toString().padLeft(2,'0')}-${_eventAt.day.toString().padLeft(2,'0')}'),
              ),
              OutlinedButton.icon(
                onPressed: () async {
                  final picked = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_eventAt));
                  if (picked != null) setState(() => _eventAt = DateTime(_eventAt.year,_eventAt.month,_eventAt.day,picked.hour,picked.minute));
                },
                icon: const Icon(Icons.schedule), label: Text('Цаг: ${TimeOfDay.fromDateTime(_eventAt).format(context)}'),
              ),
              _field('Тэмцээний газар / заал', _venue),
              Row(children: [
                Expanded(child: _field('Шүүгчийн тоо', _count, number: true)),
                const SizedBox(width: 8),
                Expanded(child: _field('Нэгж үнэ (₮)', _fee, number: true)),
              ]),
              _field('Холбоо барих хүний нэр', _contactName),
              _field('Холбоо барих утас', _contactPhone, number: true),
              _field('Нэмэлт тайлбар', _notes, maxLines: 2),
              FilledButton.icon(onPressed: _busy ? null : _createRequest, icon: const Icon(Icons.send), label: const Text('ЗАХИАЛГА ИЛГЭЭХ')),
            ])),
          )),
          if (_error != null) Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
          const SizedBox(height: 8),
          const Text('Миний захиалга, томилгоо', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          if (_busy) const LinearProgressIndicator(),
          if (_requests.isEmpty && !_busy) const Padding(padding: EdgeInsets.all(16), child: Text('Одоогоор захиалга алга.')),
          ..._requests.map((item) {
            final id = item['id'] as int;
            final status = item['status']?.toString() ?? '';
            return Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${item['sport']} • ${item['rank']}', style: const TextStyle(fontWeight: FontWeight.bold)),
              Text('${item['venue']} • ${item['event_at']}'),
              Text('Дүн: ${item['total_amount']} ₮ • Төлөв: $status'),
              if (status == 'pending') TextButton(onPressed: _busy ? null : () => _action(id, 'assign', sport: item['sport']?.toString()), child: const Text('Тохирох шүүгчид томилох')),
              if (status == 'assigned') TextButton(onPressed: _busy ? null : () => _action(id, 'accept'), child: const Text('Томилгоо зөвшөөрөх')),
              if (status == 'accepted') TextButton(onPressed: _busy ? null : () => _action(id, 'complete'), child: const Text('Ажил дууссан гэж тэмдэглэх')),
              if (status == 'completed' && item['referee_user_id'] != null) TextButton(onPressed: _busy ? null : () => _rate(id), child: const Text('Шүүгчид үнэлгээ өгөх')),
            ])));
          }),
          const SizedBox(height: 16),
          const Text('Тайлбар: Захиалгын үнийн дүн нь урьдчилсан тооцоо. Онлайн төлбөр хараахан холбогдоогүй.', style: TextStyle(fontSize: 12, color: Colors.blueGrey)),
        ]),
      ),
    );
  }
}
