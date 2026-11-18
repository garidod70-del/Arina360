import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/network/api_client.dart';

class AdminRefereePage extends StatefulWidget {
  const AdminRefereePage({super.key});

  @override
  State<AdminRefereePage> createState() => _AdminRefereePageState();
}

class _AdminRefereePageState extends State<AdminRefereePage> {
  static const _storage = FlutterSecureStorage();
  final _api = ApiClient();
  final _formKey = GlobalKey<FormState>();
  final _phone = TextEditingController();
  final _sport = TextEditingController(text: 'Жүдо');
  final _rank = TextEditingController(text: 'Улсын');
  final _region = TextEditingController(text: 'Улаанбаатар');
  final _license = TextEditingController();
  final _issuer = TextEditingController();
  final _fee = TextEditingController(text: '50000');
  final _expiry = TextEditingController();
  final _note = TextEditingController();
  int? _userId;
  bool _busy = false;
  String? _message;
  bool _approved = true;

  @override
  void dispose() {
    _api.close();
    _phone.dispose(); _sport.dispose(); _rank.dispose(); _region.dispose();
    _license.dispose(); _issuer.dispose(); _fee.dispose(); _expiry.dispose(); _note.dispose();
    super.dispose();
  }

  Future<void> _grant() async {
    if (!_formKey.currentState!.validate()) return;
    final token = await _storage.read(key: 'arena_access_token');
    if (token == null) {
      setState(() => _message = 'Нэвтрэх эрх олдсонгүй.');
      return;
    }
    setState(() { _busy = true; _message = null; });
    try {
      final body = <String, dynamic>{
        'phone': _phone.text.trim(), 'sport': _sport.text.trim(),
        'rank': _rank.text.trim(), 'region': _region.text.trim(),
        'license_number': _license.text.trim(), 'license_issuer': _issuer.text.trim(),
        'base_fee': int.parse(_fee.text.trim()),
      };
      if (_expiry.text.trim().isNotEmpty) {
        body['license_expires_at'] = DateTime.parse(_expiry.text.trim()).toUtc().toIso8601String();
      }
      final result = await _api.postAuthorized('/admin/referees/grant', token: token, body: body);
      if (!mounted) return;
      setState(() {
        _userId = result['user_id'] as int;
        _message = 'Шүүгчийн эрх олголоо. Лицензийн төлөв: шалгах шаардлагатай.';
      });
    } catch (e) {
      if (mounted) setState(() => _message = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    final id = _userId;
    if (id == null) return;
    final token = await _storage.read(key: 'arena_access_token');
    if (token == null) return;
    setState(() { _busy = true; _message = null; });
    try {
      final result = await _api.postAuthorized(
        '/admin/referees/$id/verify', token: token,
        body: {'approved': _approved, 'note': _note.text.trim()},
      );
      if (mounted) setState(() => _message = 'Баталгаажуулалтын төлөв: ${result['verification_status']}');
    } catch (e) {
      if (mounted) setState(() => _message = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _field(String label, TextEditingController controller, {bool number = false, bool required = true, String? hint}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextFormField(
        controller: controller,
        keyboardType: number ? TextInputType.number : TextInputType.text,
        decoration: InputDecoration(labelText: label, hintText: hint),
        validator: (value) {
          if (required && (value ?? '').trim().isEmpty) return 'Энэ талбарыг бөглөнө үү';
          if (number && (value ?? '').trim().isNotEmpty && int.tryParse(value!.trim()) == null) return 'Бүхэл тоо оруулна уу';
          return null;
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Админ • Шүүгчийн эрх')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Шүүгчийн бүртгэл ба лиценз', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        const Text('Эхлээд хэрэглэгчид шүүгчийн эрх олгоно. Дараа нь эх лицензийг шалгаж байж баталгаажуулна.'),
        const SizedBox(height: 14),
        Form(key: _formKey, child: Column(children: [
          _field('Хэрэглэгчийн утас', _phone, hint: '+976...'),
          _field('Спортын төрөл', _sport),
          _field('Шүүгчийн зэрэглэл', _rank),
          _field('Бүс / аймаг', _region),
          _field('Лицензийн дугаар', _license),
          _field('Лиценз олгосон байгууллага', _issuer),
          _field('Хөлсний суурь дүн (₮)', _fee, number: true),
          _field('Лиценз дуусах огноо (заавал биш)', _expiry, required: false, hint: 'YYYY-MM-DD'),
          FilledButton.icon(
            onPressed: _busy ? null : _grant,
            icon: const Icon(Icons.person_add_alt_1),
            label: const Text('ШҮҮГЧИЙН ЭРХ ОЛГОХ'),
          ),
        ])),
        if (_userId != null) ...[
          const Divider(height: 28),
          Text('Хэрэглэгчийн ID: $_userId', style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          DropdownButtonFormField<bool>(
            value: _approved,
            decoration: const InputDecoration(labelText: 'Лицензийн шийдвэр'),
            items: const [
              DropdownMenuItem(value: true, child: Text('Баталгаажуулах')),
              DropdownMenuItem(value: false, child: Text('Татгалзах')),
            ],
            onChanged: (v) => setState(() => _approved = v ?? true),
          ),
          const SizedBox(height: 10),
          _field('Шалгалтын тэмдэглэл', _note, required: false),
          FilledButton.icon(
            onPressed: _busy ? null : _verify,
            icon: const Icon(Icons.verified_user),
            label: const Text('ШИЙДВЭР БҮРТГЭХ'),
          ),
        ],
        if (_busy) const LinearProgressIndicator(),
        if (_message != null) Padding(
          padding: const EdgeInsets.only(top: 14),
          child: Text(_message!, style: const TextStyle(fontWeight: FontWeight.w600)),
        ),
      ]),
    );
  }
}
