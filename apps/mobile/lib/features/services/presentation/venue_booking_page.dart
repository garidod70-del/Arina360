import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';

class VenueBookingPage extends StatefulWidget {
  const VenueBookingPage({super.key});

  @override
  State<VenueBookingPage> createState() => _VenueBookingPageState();
}

class _VenueBookingPageState extends State<VenueBookingPage> {
  static const _storage = FlutterSecureStorage();
  final ApiClient _api = ApiClient();
  final _sport = TextEditingController(text: 'Жүдо');
  final _region = TextEditingController();
  DateTime _selectedDate = DateTime.now().add(const Duration(days: 1));
  List<Map<String, dynamic>> _slots = [];
  List<Map<String, dynamic>> _bookings = [];
  bool _loading = false;
  bool _saving = false;
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
    _sport.dispose();
    _region.dispose();
    super.dispose();
  }

  String _dateText(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    if (!ApiConfig.isConfigured) {
      setState(() => _error = 'Заалын цагийн хуваарь ашиглахын тулд серверийн холболт шаардлагатай.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final token = await _token();
      if (token == null || token.isEmpty) throw const ApiException(401, 'Эхлээд нэвтэрнэ үү.');
      final query = <String, String>{
        'booking_date': _dateText(_selectedDate),
        if (_sport.text.trim().isNotEmpty) 'sport': _sport.text.trim(),
        if (_region.text.trim().isNotEmpty) 'region': _region.text.trim(),
      };
      final slots = await _api.getList('/venues/slots?${Uri(queryParameters: query).query}', token: token);
      final bookings = await _api.getList('/venues/bookings/me', token: token);
      if (!mounted) return;
      setState(() { _slots = slots; _bookings = bookings; });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _book(Map<String, dynamic> slot) async {
    final phone = TextEditingController();
    final purpose = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Заал захиалах'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${slot['venue_name']}\n${slot['booking_date']} • ${slot['start_time']}–${slot['end_time']}'),
            const SizedBox(height: 12),
            TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Холбоо барих утас')),
            const SizedBox(height: 10),
            TextField(controller: purpose, decoration: const InputDecoration(labelText: 'Зорилго (заавал биш)')),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('БОЛИХ')),
          FilledButton(onPressed: () {
            if (phone.text.trim().length < 8) {
              ScaffoldMessenger.of(dialogContext).showSnackBar(const SnackBar(content: Text('Утасны дугаараа зөв оруулна уу.')));
              return;
            }
            Navigator.pop(dialogContext, true);
          }, child: const Text('ЗАХИАЛАХ')),
        ],
      ),
    );
    if (ok != true) { phone.dispose(); purpose.dispose(); return; }
    await _perform('/venues/slots/${slot['id']}/book', {
      'contact_phone': phone.text.trim(),
      'purpose': purpose.text.trim().isEmpty ? null : purpose.text.trim(),
    });
    phone.dispose();
    purpose.dispose();
  }

  Future<void> _perform(String path, Map<String, dynamic> body) async {
    final token = await _token();
    if (token == null) return;
    setState(() => _saving = true);
    try {
      await _api.postAuthorized(path, token: token, body: body);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Үйлдэл амжилттай бүртгэгдлээ.')));
      await _load();
    } catch (error) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _addSlot() async {
    final name = TextEditingController();
    final address = TextEditingController();
    final sport = TextEditingController(text: _sport.text);
    final start = TextEditingController(text: '10:00');
    final end = TextEditingController(text: '11:00');
    final price = TextEditingController(text: '40000');
    final formKey = GlobalKey<FormState>();
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Сул цаг нэмэх'),
        content: SizedBox(
          width: 420,
          child: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                _field(name, 'Заалны нэр'),
                _field(address, 'Байршил, хаяг'),
                _field(sport, 'Спортын төрөл'),
                Row(children: [
                  Expanded(child: _field(start, 'Эхлэх цаг (HH:MM)')),
                  const SizedBox(width: 8),
                  Expanded(child: _field(end, 'Дуусах цаг (HH:MM)')),
                ]),
                _field(price, 'Үнэ (₮)', numeric: true),
              ]),
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('БОЛИХ')),
          FilledButton(onPressed: () {
            if (!formKey.currentState!.validate()) return;
            if (TimeOfDayFormat.HH_colon_mm.name.isEmpty) return;
            Navigator.pop(dialogContext, true);
          }, child: const Text('ЦАГ НЭМЭХ')),
        ],
      ),
    );
    if (ok == true) {
      final token = await _token();
      if (token != null) {
        setState(() => _saving = true);
        try {
          await _api.postAuthorized('/venues/slots', token: token, body: {
            'venue_name': name.text.trim(),
            'venue_address': address.text.trim(),
            'sport': sport.text.trim(),
            'booking_date': _dateText(_selectedDate),
            'start_time': '${start.text.trim()}:00',
            'end_time': '${end.text.trim()}:00',
            'price': int.tryParse(price.text.trim()) ?? 0,
          });
          await _load();
        } catch (error) {
          if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
        } finally {
          if (mounted) setState(() => _saving = false);
        }
      }
    }
    name.dispose(); address.dispose(); sport.dispose(); start.dispose(); end.dispose(); price.dispose();
  }

  Widget _field(TextEditingController controller, String label, {bool numeric = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextFormField(
        controller: controller,
        keyboardType: numeric ? TextInputType.number : TextInputType.text,
        decoration: InputDecoration(labelText: label),
        validator: (value) => (value ?? '').trim().isEmpty ? 'Энэ талбарыг бөглөнө үү.' : null,
      ),
    );
  }

  String _status(String? value) {
    switch (value) {
      case 'pending': return 'Хариу хүлээж байна';
      case 'confirmed': return 'Баталгаажсан';
      case 'rejected': return 'Татгалзсан';
      case 'cancelled': return 'Цуцалсан';
      default: return value ?? '—';
    }
  }

  String _price(dynamic value) {
    final amount = value is num ? value.toInt() : int.tryParse('$value') ?? 0;
    return amount == 0 ? 'Үнийг тохиролцоно' : '${amount.toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')} ₮';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Заал захиалга'), actions: [
        IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
      ]),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF101B36), Color(0xFF244B91)]),
              borderRadius: BorderRadius.circular(18),
            ),
            child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.stadium, color: Colors.white, size: 34),
              SizedBox(height: 10),
              Text('СПОРТЫН ЗААЛ, ТАЛБАЙ', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20)),
              SizedBox(height: 6),
              Text('Сул цагийг хараад хүссэн өдрөө захиалаарай.', style: TextStyle(color: Colors.white70)),
            ]),
          ),
          const SizedBox(height: 14),
          Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.calendar_month),
              title: const Text('Захиалах өдөр'),
              subtitle: Text(_dateText(_selectedDate)),
              trailing: const Icon(Icons.edit_calendar),
              onTap: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: _selectedDate,
                  firstDate: DateTime.now(),
                  lastDate: DateTime.now().add(const Duration(days: 180)),
                );
                if (picked != null) { setState(() => _selectedDate = picked); await _load(); }
              },
            ),
            TextField(controller: _sport, decoration: const InputDecoration(labelText: 'Спортын төрөл', prefixIcon: Icon(Icons.sports))),
            const SizedBox(height: 10),
            TextField(controller: _region, decoration: const InputDecoration(labelText: 'Байршил / дүүрэг', prefixIcon: Icon(Icons.location_on_outlined))),
            const SizedBox(height: 10),
            SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: _loading ? null : _load, icon: const Icon(Icons.search), label: const Text('СУЛ ЦАГ ХАЙХ'))),
          ]))),
          const SizedBox(height: 14),
          Row(children: [
            const Expanded(child: Text('СУЛ ЦАГИЙН ЖАГСААЛТ', style: TextStyle(fontWeight: FontWeight.w900))),
            Text('${_slots.length} цаг'),
          ]),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text(_error!, style: const TextStyle(color: Colors.red))),
          if (!_loading && _slots.isEmpty && _error == null)
            const Card(child: Padding(padding: EdgeInsets.all(18), child: Text('Энэ өдөрт тохирох сул цаг олдсонгүй. Өөр өдөр сонгоод хайна уу.'))),
          ..._slots.map((slot) => Card(
            margin: const EdgeInsets.only(top: 10),
            child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(slot['venue_name']?.toString() ?? 'Спортын заал', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 5),
              Text(slot['venue_address']?.toString() ?? ''),
              Text('${slot['sport']} • ${slot['start_time']}–${slot['end_time']}'),
              const SizedBox(height: 8),
              Text(_price(slot['price']), style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF245FC7))),
              const SizedBox(height: 8),
              SizedBox(width: double.infinity, child: FilledButton(onPressed: _saving ? null : () => _book(slot), child: const Text('ЭНЭ ЦАГИЙГ ЗАХИАЛАХ'))),
            ])),
          )),
          const SizedBox(height: 18),
          OutlinedButton.icon(onPressed: _saving ? null : _addSlot, icon: const Icon(Icons.add_business), label: const Text('ЗААЛЫНХАА СУЛ ЦАГИЙГ НЭМЭХ')),
          const SizedBox(height: 20),
          const Text('МИНИЙ ЗАХИАЛГУУД', style: TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          if (_bookings.isEmpty) const Text('Одоогоор захиалга алга.'),
          ..._bookings.map((booking) => Card(
            child: ListTile(
              leading: const Icon(Icons.event_available),
              title: Text('Захиалга #${booking['id']}'),
              subtitle: Text(_status(booking['status']?.toString())),
              trailing: booking['status'] == 'pending' || booking['status'] == 'confirmed'
                  ? TextButton(onPressed: _saving ? null : () => _perform('/venues/bookings/${booking['id']}/cancel', {}), child: const Text('Цуцлах'))
                  : null,
            ),
          )),
          const SizedBox(height: 14),
          const Text('Тайлбар: Заал эзэмшигчийн бүртгэл админаар баталгаажсан байх шаардлагатай. Захиалга эхлээд хүсэлт хэлбэрээр очиж, эзэмшигч баталгаажуулна.', style: TextStyle(fontSize: 12, color: Colors.blueGrey)),
        ]),
      ),
    );
  }
}
