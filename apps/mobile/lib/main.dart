import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:open_filex/open_filex.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/config/api_config.dart';
import 'core/network/api_client.dart';
import 'features/auth/data/auth_repository.dart';
import 'features/auth/domain/auth_session.dart';
import 'features/services/domain/service_item.dart';

void main() => runApp(const Arena360App());

const navy = Color(0xFF101B36);
const blue = Color(0xFF2878FF);
const pageBg = Color(0xFFF4F7FC);

class Arena360App extends StatelessWidget {
  const Arena360App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ARENA 360',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: blue),
        scaffoldBackgroundColor: pageBg,
        appBarTheme: const AppBarTheme(
          backgroundColor: navy,
          foregroundColor: Colors.white,
          centerTitle: false,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
          ),
        ),
      ),
      home: const AuthPage(),
    );
  }
}

class AuthPage extends StatefulWidget {
  const AuthPage({super.key});

  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final _formKey = GlobalKey<FormState>();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _isRegister = false;
  bool _showPassword = false;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  String? _validatePhone(String? value) {
    return (value ?? '').trim().isNotEmpty
        ? null
        : 'Утасны дугаар оруулна уу';
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || _isSubmitting) return;

    if (!ApiConfig.isConfigured) {
      // Keeps the existing prototype usable until the API is deployed.
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => HomePage(phone: _phone.text.trim()),
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    final api = ApiClient();
    try {
      final repository = AuthRepository(api);
      final response = _isRegister
          ? await repository.register(
              phone: _phone.text.trim(),
              password: _password.text,
            )
          : await repository.login(
              phone: _phone.text.trim(),
              password: _password.text,
            );
      final session = AuthSession.fromJson(response);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('arena_access_token', session.accessToken);
      await prefs.setStringList('arena_user_roles', session.roles);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => HomePage(phone: session.phone),
        ),
      );
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.message)),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Сервертэй холбогдож чадсангүй. Дахин оролдоно уу.')),
        );
      }
    } finally {
      api.close();
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      height: 76,
                      width: 76,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: navy,
                        borderRadius: BorderRadius.circular(22),
                      ),
                      child: const Icon(
                        Icons.sports_martial_arts,
                        color: Colors.white,
                        size: 42,
                      ),
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      'ARENA 360',
                      style: TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.w900,
                        color: navy,
                        letterSpacing: 1.4,
                      ),
                    ),
                    const Text(
                      'ONE PLATFORM. ALL SPORTS.',
                      style: TextStyle(color: blue, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 32),
                    Text(
                      _isRegister ? 'Шинэ хэрэглэгч бүртгүүлэх' : 'Нэвтрэх',
                      style: const TextStyle(
                        fontSize: 23,
                        fontWeight: FontWeight.bold,
                        color: navy,
                      ),
                    ),
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: _phone,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(
                        labelText: 'Утасны дугаар',
                        prefixIcon: Icon(Icons.phone),
                        counterText: '',
                      ),
                      validator: _validatePhone,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: !_showPassword,
                      decoration: InputDecoration(
                        labelText: 'Нууц үг',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          onPressed: () => setState(
                            () => _showPassword = !_showPassword,
                          ),
                          icon: Icon(
                            _showPassword
                                ? Icons.visibility_off
                                : Icons.visibility,
                          ),
                        ),
                      ),
                      validator: (value) =>
                          value == null || value.isEmpty
                              ? 'Нууц үг оруулна уу'
                              : null,
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      height: 52,
                      child: FilledButton(
                        style: FilledButton.styleFrom(backgroundColor: blue),
                        onPressed: _isSubmitting ? null : _submit,
                        child: _isSubmitting
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Text(_isRegister ? 'БҮРТГҮҮЛЭХ' : 'НЭВТРЭХ'),
                      ),
                    ),
                    TextButton(
                      onPressed: () => setState(() {
                        _isRegister = !_isRegister;
                        _formKey.currentState?.reset();
                      }),
                      child: Text(
                        _isRegister
                            ? 'Бүртгэлтэй юу? Нэвтрэх'
                            : 'Шинэ хэрэглэгч үү? Бүртгүүлэх',
                      ),
                    ),
                    Text(
                      ApiConfig.isConfigured
                          ? 'Нэгдсэн серверийн бүртгэл ашиглаж байна.'
                          : 'Туршилтын горим: серверийн хаяг тохируулах хүртэл нэвтрэлт төхөөрөмж дээр туршилтаар ажиллана.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 11, color: Colors.blueGrey),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  final String phone;
  const HomePage({super.key, required this.phone});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _checkForUpdateNotice());
  }

  Future<void> _checkForUpdateNotice() async {
    try {
      final manifest = await http.get(Uri.parse(
        'https://raw.githubusercontent.com/garidod70-del/Arina360/main/apps/mobile/version.json',
      )).timeout(const Duration(seconds: 12));
      if (manifest.statusCode != 200 || !mounted) return;
      final data = jsonDecode(manifest.body) as Map<String, dynamic>;
      final info = await PackageInfo.fromPlatform();
      final installed = int.tryParse(info.buildNumber) ?? 0;
      final latest = (data['buildNumber'] as num).toInt();
      if (latest <= installed || !mounted) return;
      showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('ARENA 360 шинэчлэлт'),
          content: Text('Шинэ хувилбар ${data['version']} бэлэн байна. Одоо шинэчлэх үү?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Дараа'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const AppUpdatePage()),
                );
              },
              child: const Text('ШИНЭЧЛЭХ'),
            ),
          ],
        ),
      );
    } catch (_) {
      // Keep the home screen usable when the network is unavailable.
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ARENA 360'),
        actions: [
          IconButton(
            tooltip: 'Миний профайл',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => ProfilePage(phone: widget.phone),
              ),
            ),
            icon: const Icon(Icons.account_circle_outlined),
          ),
          IconButton(
            tooltip: 'Шинэчлэлт шалгах',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AppUpdatePage()),
            ),
            icon: const Icon(Icons.system_update_alt),
          ),
          IconButton(
            tooltip: 'Гарах',
            onPressed: () => Navigator.of(context).pushAndRemoveUntil(
              MaterialPageRoute(builder: (_) => const AuthPage()),
              (_) => false,
            ),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [navy, Color(0xFF244B91)],
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'ONE PLATFORM. ALL SPORTS.',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Тавтай морил, ${widget.phone}',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          const Text(
            'ҮЙЛЧИЛГЭЭНҮҮД',
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w900,
              color: navy,
            ),
          ),
          const SizedBox(height: 12),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: services.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.05,
            ),
            itemBuilder: (context, index) {
              final service = services[index];
              return InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => index == 0 ? const RefereeBookingPage() : ServicePage(service: service),
                  ),
                ),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFFE5EAF2)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Icon(service.icon, color: blue, size: 30),
                      Text(
                        service.name,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          color: navy,
                        ),
                      ),
                      const Icon(Icons.arrow_forward, color: blue, size: 18),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}


const refereeSports = <String, List<String>>{
  'Багийн спорт': ['Сагсан бөмбөг', 'Волейбол', '3x3', 'Хөлбөмбөг'],
  'Ганцаарчилсан спорт': ['Жүдо', 'Чөлөөт бөх'],
  'Үндэсний спорт': ['Үндэсний бөх', 'Шагайн харваа'],
};

const refereeRanks = <String, List<String>>{
  'Багийн спорт': ['Олон улсын', 'Улсын', 'I зэрэг', 'II зэрэг', 'III зэрэг'],
  'Ганцаарчилсан спорт': ['Олон улсын', 'Улсын', 'I зэрэг', 'II зэрэг', 'III зэрэг'],
  'Үндэсний бөх': ['Улсын цолтой', 'Аймгийн цолтой', 'Сумын цолтой', 'Засуул', 'Гарын даа'],
  'Шагайн харваа': ['Улсын цолтой', 'Аймгийн цолтой', 'Зэрэгтэй шүүгч'],
};

class RefereeBookingPage extends StatefulWidget {
  const RefereeBookingPage({super.key});
  @override
  State<RefereeBookingPage> createState() => _RefereeBookingPageState();
}

class _RefereeBookingPageState extends State<RefereeBookingPage> {
  final _formKey = GlobalKey<FormState>();
  final _count = TextEditingController(text: '1');
  final _rate = TextEditingController(text: '50000');
  final _days = TextEditingController(text: '1');
  final _transport = TextEditingController(text: '0');
  final _food = TextEditingController(text: '0');
  final _venue = TextEditingController();
  final _contactName = TextEditingController();
  final _contactPhone = TextEditingController();
  final _notes = TextEditingController();

  String role = 'Тэмцээн зохион байгуулагч';
  String category = 'Багийн спорт';
  String sport = 'Сагсан бөмбөг';
  String rank = 'Улсын';
  String booking = 'Нэг шүүгч';
  String payment = 'Нэг тоглолтоор';
  DateTime? eventDate;
  TimeOfDay? eventTime;
  bool addTransport = false;
  bool addFood = false;

  List<String> get ranks {
    if (category == 'Үндэсний спорт') {
      return sport == 'Үндэсний бөх'
          ? refereeRanks['Үндэсний бөх']!
          : refereeRanks['Шагайн харваа']!;
    }
    return refereeRanks[category]!;
  }

  int _number(TextEditingController c) => int.tryParse(c.text.trim()) ?? 0;
  int _bounded(TextEditingController c, int max) =>
      _number(c).clamp(0, max).toInt();

  int get baseAmount {
    final people = _bounded(_count, 10000);
    final unitPrice = _bounded(_rate, 100000000);
    final days = payment == 'Нэг өдрөөр'
        ? _bounded(_days, 365).clamp(1, 365).toInt()
        : 1;
    return people * unitPrice * days;
  }

  int get totalAmount =>
      baseAmount +
      (addTransport ? _bounded(_transport, 100000000) : 0) +
      (addFood ? _bounded(_food, 100000000) : 0);

  @override
  void dispose() {
    _count.dispose();
    _rate.dispose();
    _days.dispose();
    _transport.dispose();
    _food.dispose();
    _venue.dispose();
    _contactName.dispose();
    _contactPhone.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _chooseDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: eventDate ?? now,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: DateTime(now.year + 3),
      helpText: 'ТЭМЦЭЭНИЙ ОГНОО СОНГОХ',
    );
    if (picked != null) setState(() => eventDate = picked);
  }

  Future<void> _chooseTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: eventTime ?? const TimeOfDay(hour: 9, minute: 0),
      helpText: 'ЭХЛЭХ ЦАГ СОНГОХ',
    );
    if (picked != null) setState(() => eventTime = picked);
  }

  String _dateText(DateTime? d) => d == null
      ? 'Огноо сонгох'
      : d.year.toString() + '-' +
          d.month.toString().padLeft(2, '0') + '-' +
          d.day.toString().padLeft(2, '0');

  String _money(int amount) => amount.toString().replaceAllMapped(
        RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
        (match) => match[1]! + ',',
      ) + ' ₮';

  Widget _section(String title, Widget child) => Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(
                fontWeight: FontWeight.w800, color: navy, fontSize: 15)),
            const SizedBox(height: 8),
            child,
          ],
        ),
      );

  Widget _dropdown(String label, String value, List<String> values,
          ValueChanged<String?> onChanged) =>
      DropdownButtonFormField<String>(
        value: value,
        isExpanded: true,
        decoration: InputDecoration(labelText: label),
        items: values.map((v) =>
            DropdownMenuItem(value: v, child: Text(v))).toList(),
        onChanged: onChanged,
      );

  Widget _numberField(String label, TextEditingController c,
      {bool required = true}) =>
      TextFormField(
        controller: c,
        keyboardType: TextInputType.number,
        onChanged: (_) => setState(() {}),
        decoration: InputDecoration(labelText: label),
        validator: (value) {
          final number = int.tryParse((value ?? '').trim());
          if (required && (number == null || number <= 0)) {
            return '0-ээс их бүхэл тоо оруулна уу';
          }
          if (!required && (number == null || number < 0)) {
            return 'Зөв дүн оруулна уу';
          }
          return null;
        },
      );

  Widget _summaryLine(String label, String value, {bool strong = false}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: Text(label,
                style: TextStyle(color: Colors.blueGrey.shade700, fontSize: 13))),
            const SizedBox(width: 8),
            Flexible(child: Text(value.isEmpty ? '—' : value,
                textAlign: TextAlign.end,
                style: TextStyle(fontSize: 13,
                    fontWeight: strong ? FontWeight.w900 : FontWeight.w600,
                    color: strong ? blue : navy))),
          ],
        ),
      );

  void _prepareRequest() {
    if (!_formKey.currentState!.validate()) return;
    if (eventDate == null || eventTime == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Тэмцээний огноо, эхлэх цагийг сонгоно уу.')));
      return;
    }

    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('ШҮҮГЧИЙН ХҮСЭЛТИЙН НЭГТГЭЛ'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _summaryLine('Хүсэлт гаргагч', role),
              _summaryLine('Спорт', category + ' / ' + sport),
              _summaryLine('Зэрэглэл / үүрэг', rank),
              _summaryLine('Захиалгын төрөл', booking),
              _summaryLine('Огноо', _dateText(eventDate)),
              _summaryLine('Эхлэх цаг', eventTime!.format(context)),
              _summaryLine('Байршил', _venue.text.trim()),
              _summaryLine('Шүүгчийн тоо', _count.text.trim()),
              _summaryLine('Холбоо барих', _contactName.text.trim() +
                  ' / ' + _contactPhone.text.trim()),
              const Divider(),
              _summaryLine('Үндсэн төлбөр', _money(baseAmount)),
              if (addTransport)
                _summaryLine('Унаа', _money(_bounded(_transport, 100000000))),
              if (addFood)
                _summaryLine('Хоол', _money(_bounded(_food, 100000000))),
              _summaryLine('НИЙТ ДҮН', _money(totalAmount), strong: true),
              if (_notes.text.trim().isNotEmpty) ...[
                const SizedBox(height: 8),
                const Text('Нэмэлт хүсэлт',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                Text(_notes.text.trim()),
              ],
              const SizedBox(height: 12),
              const Text(
                'Энэ нь урьдчилсан хүсэлтийн нэгтгэл. Одоогоор серверт илгээгдэхгүй; бодит захиалга баталгаажуулахад серверийн холболт шаардлагатай.',
                style: TextStyle(fontSize: 12, color: Colors.blueGrey),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('ЗАСАХ')),
          FilledButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('ОЙЛГОМЖТОЙ')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Шүүгчийн үйлчилгээ')),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [navy, Color(0xFF244B91)]),
              borderRadius: BorderRadius.circular(18)),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('ARENA 360 / REFEREE',
                    style: TextStyle(color: Colors.white70,
                        fontWeight: FontWeight.bold)),
                SizedBox(height: 8),
                Text('Шүүгчийн захиалгын төв',
                    style: TextStyle(color: Colors.white, fontSize: 22,
                        fontWeight: FontWeight.w900)),
                SizedBox(height: 6),
                Text('Спорт, зэрэглэл, огноо болон зардлаа нэг дороос тохируул.',
                    style: TextStyle(color: Colors.white70)),
              ],
            ),
          ),
          const SizedBox(height: 20),
          _section('1. Хэрэглэгчийн төрөл',
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'Тэмцээн зохион байгуулагч',
                    label: Text('Зохион байгуулагч')),
                ButtonSegment(value: 'Шүүгч', label: Text('Шүүгч')),
              ],
              selected: {role},
              onSelectionChanged: (values) =>
                  setState(() => role = values.first),
            )),
          _section('2. Спортын ангилал',
            _dropdown('Ангилал', category, refereeSports.keys.toList(), (value) {
              if (value == null) return;
              setState(() {
                category = value;
                sport = refereeSports[category]!.first;
                rank = ranks.first;
              });
            })),
          _section('Спортын төрөл',
            _dropdown('Спорт', sport, refereeSports[category]!, (value) {
              if (value == null) return;
              setState(() {
                sport = value;
                rank = ranks.first;
              });
            })),
          _section('3. Шүүгчийн зэрэглэл / үүрэг',
            _dropdown('Зэрэглэл', rank, ranks,
                (value) => setState(() => rank = value!))),
          _section('4. Захиалгын төрөл',
            _dropdown('Захиалгын багц', booking, const [
              'Нэг шүүгч',
              'Шүүгчдийн баг (Crew)',
              'Спартакиад / спортын наадмын багц',
            ], (value) => setState(() => booking = value!))),
          _section('5. Тэмцээний мэдээлэл', Column(children: [
            Row(children: [
              Expanded(child: OutlinedButton.icon(
                onPressed: _chooseDate,
                icon: const Icon(Icons.calendar_month),
                label: Text(_dateText(eventDate)))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(
                onPressed: _chooseTime,
                icon: const Icon(Icons.schedule),
                label: Text(eventTime == null
                    ? 'Цаг сонгох' : eventTime!.format(context)))),
            ]),
            const SizedBox(height: 10),
            TextFormField(
              controller: _venue,
              decoration: const InputDecoration(
                labelText: 'Тэмцээн болох газар / заал',
                prefixIcon: Icon(Icons.location_on_outlined)),
              validator: (v) => (v ?? '').trim().isEmpty
                  ? 'Байршил оруулна уу' : null),
          ])),
          _section('6. Төлбөрийн тооцоолол', Column(children: [
            _dropdown('Тооцох хэлбэр', payment, const [
              'Нэг тоглолтоор', 'Нэг өдрөөр', 'Нэг даваагаар',
            ], (value) => setState(() => payment = value!)),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: _numberField('Шүүгчийн тоо', _count)),
              const SizedBox(width: 10),
              Expanded(child: _numberField('Нэгж үнэ (₮)', _rate)),
            ]),
            if (payment == 'Нэг өдрөөр') ...[
              const SizedBox(height: 10),
              _numberField('Ажиллах өдөр', _days),
            ],
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Унааны зардал нэмэх'),
              value: addTransport,
              onChanged: (v) => setState(() => addTransport = v)),
            if (addTransport)
              _numberField('Нийт унааны зардал (₮)', _transport,
                  required: false),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Хоолны зардал нэмэх'),
              value: addFood,
              onChanged: (v) => setState(() => addFood = v)),
            if (addFood)
              _numberField('Нийт хоолны зардал (₮)', _food, required: false),
          ])),
          _section('7. Холбоо барих мэдээлэл', Column(children: [
            TextFormField(
              controller: _contactName,
              decoration: const InputDecoration(
                labelText: 'Холбоо барих хүний нэр',
                prefixIcon: Icon(Icons.person_outline)),
              validator: (v) => (v ?? '').trim().isEmpty
                  ? 'Нэрээ оруулна уу' : null),
            const SizedBox(height: 10),
            TextFormField(
              controller: _contactPhone,
              keyboardType: TextInputType.phone,
              maxLength: 8,
              decoration: const InputDecoration(
                labelText: 'Утасны дугаар',
                prefixIcon: Icon(Icons.phone), counterText: ''),
              validator: (v) => (v ?? '').trim().length < 8
                  ? '8 оронтой утасны дугаар оруулна уу' : null),
            const SizedBox(height: 10),
            TextFormField(
              controller: _notes,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Нэмэлт тайлбар (заавал биш)',
                alignLabelWithHint: true,
                prefixIcon: Icon(Icons.notes)),
            ),
          ])),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFDCE5F2))),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('ТӨЛБӨРИЙН НЭГТГЭЛ',
                    style: TextStyle(color: navy, fontWeight: FontWeight.w900)),
                const SizedBox(height: 10),
                _summaryLine('Үндсэн төлбөр', _money(baseAmount)),
                if (addTransport)
                  _summaryLine('Унаа', _money(_bounded(_transport, 100000000))),
                if (addFood)
                  _summaryLine('Хоол', _money(_bounded(_food, 100000000))),
                const Divider(height: 22),
                _summaryLine('НИЙТ ДҮН', _money(totalAmount), strong: true),
                const SizedBox(height: 5),
                const Text(
                  'Жишиг тариф. Эцсийн үнийг шүүгч болон захиалагч харилцан баталгаажуулна.',
                  style: TextStyle(fontSize: 11, color: Colors.blueGrey)),
              ],
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 54,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: blue,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14))),
              onPressed: _prepareRequest,
              icon: const Icon(Icons.assignment_turned_in_outlined),
              label: const Text('ЗАХИАЛГЫН ХҮСЭЛТ БЭЛТГЭХ',
                  style: TextStyle(fontWeight: FontWeight.w800)),
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Одоогийн хувилбар хүсэлтийг шалгаж, нэгтгэл харуулна. Онлайн илгээлт, бодит шүүгчийн жагсаалт болон төлбөрийн баталгаажуулалт серверийн холболт нэмсний дараа ажиллана.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: Colors.blueGrey)),
          const SizedBox(height: 24),
        ],
      ),
    ),
  );
}

class ServicePage extends StatelessWidget {
  final ServiceItem service;
  const ServicePage({super.key, required this.service});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(service.name)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(service.icon, color: blue, size: 64),
              const SizedBox(height: 18),
              Text(
                service.name,
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: navy,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 10),
              Text(service.description, textAlign: TextAlign.center),
              const SizedBox(height: 20),
              const Text(
                'Энэ хэсгийн бодит захиалга, төлбөр болон үйлчилгээ үзүүлэгчийн холболт дараагийн хөгжүүлэлтийн шатанд нэмэгдэнэ.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.blueGrey, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}


class AppUpdatePage extends StatefulWidget {
  const AppUpdatePage({super.key});
  @override
  State<AppUpdatePage> createState() => _AppUpdatePageState();
}

class _AppUpdatePageState extends State<AppUpdatePage> {
  static final Uri manifestUri = Uri.parse('https://raw.githubusercontent.com/garidod70-del/Arina360/main/apps/mobile/version.json');
  bool checking = false, downloading = false;
  String status = 'Шинэ хувилбар байгаа эсэхийг шалгана уу.';
  String? latestVersion, releaseNotes, apkUrl;
  int? latestBuild;

  @override
  void initState() { super.initState(); checkUpdate(showCurrent: false); }

  Future<void> checkUpdate({bool showCurrent = true}) async {
    setState(() { checking = true; status = 'Шинэчлэлт шалгаж байна...'; });
    try {
      final response = await http.get(manifestUri).timeout(const Duration(seconds: 20));
      if (response.statusCode != 200) throw Exception('Мэдээлэл татаж чадсангүй (' + response.statusCode.toString() + ').');
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final info = await PackageInfo.fromPlatform();
      final installedBuild = int.tryParse(info.buildNumber) ?? 0;
      final build = (data['buildNumber'] as num).toInt();
      if (!mounted) return;
      setState(() {
        latestBuild = build;
        latestVersion = data['version']?.toString() ?? '';
        releaseNotes = data['releaseNotes']?.toString() ?? '';
        apkUrl = data['apkUrl']?.toString();
        status = build > installedBuild
            ? 'Шинэ хувилбар бэлэн байна: ' + latestVersion!
            : 'Таны ARENA 360 хамгийн сүүлийн хувилбар байна.';
      });
      if (build <= installedBuild && showCurrent && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Апп хамгийн сүүлийн хувилбартай байна.')));
      }
    } catch (e) {
      if (mounted) setState(() => status = 'Шалгалт амжилтгүй: ' + e.toString());
    } finally {
      if (mounted) setState(() => checking = false);
    }
  }

  Future<void> downloadAndInstall() async {
    final url = apkUrl;
    if (url == null || !url.startsWith('https://')) {
      setState(() => status = 'Шинэ хувилбарын татах холбоос буруу байна.');
      return;
    }
    setState(() { downloading = true; status = 'Шинэ хувилбарыг татаж байна...'; });
    try {
      final permission = await Permission.requestInstallPackages.request();
      if (!permission.isGranted) {
        if (mounted) setState(() => status = 'APK суулгах зөвшөөрөл шаардлагатай. ARENA 360-д зөвшөөрөл өгнө үү.');
        await openAppSettings();
        return;
      }
      final response = await http.get(Uri.parse(url)).timeout(const Duration(minutes: 3));
      if (response.statusCode != 200 || response.bodyBytes.isEmpty) {
        throw Exception('APK таталт амжилтгүй (' + response.statusCode.toString() + ').');
      }
      final dir = await getTemporaryDirectory();
      final file = File(dir.path + '/arena360-update.apk');
      await file.writeAsBytes(response.bodyBytes, flush: true);
      if (!mounted) return;
      setState(() => status = 'Таталт дууслаа. Android суулгагч нээгдэж байна...');
      final result = await OpenFilex.open(file.path, type: 'application/vnd.android.package-archive');
      if (mounted && result.type != ResultType.done) {
        setState(() => status = 'Суулгагч нээгдсэнгүй: ' + result.message);
      }
    } catch (e) {
      if (mounted) setState(() => status = 'Шинэчлэлт амжилтгүй: ' + e.toString());
    } finally {
      if (mounted) setState(() => downloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasUpdate = latestBuild != null && latestVersion != null && latestBuild! > 0 && apkUrl != null;
    return Scaffold(
      appBar: AppBar(title: const Text('ARENA 360 шинэчлэлт')),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(gradient: const LinearGradient(colors: [navy, Color(0xFF244B91)]), borderRadius: BorderRadius.circular(18)),
          child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.system_update_alt, color: Colors.white, size: 38),
            SizedBox(height: 12),
            Text('ARENA 360 UPDATE', style: TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w900)),
            SizedBox(height: 6),
            Text('Шинэ хувилбарыг шалгаж, утсан дээрээ шинэчлээрэй.', style: TextStyle(color: Colors.white70)),
          ]),
        ),
        const SizedBox(height: 20),
        FutureBuilder<PackageInfo>(
          future: PackageInfo.fromPlatform(),
          builder: (context, snapshot) => Text(
            snapshot.hasData ? 'Суулгасан хувилбар: ' + snapshot.data!.version + ' (' + snapshot.data!.buildNumber + ')' : 'Суулгасан хувилбарыг уншиж байна...',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: 14),
        Text(status, style: const TextStyle(fontSize: 15)),
        if ((releaseNotes ?? '').isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text('Шинэ хувилбарын өөрчлөлт', style: TextStyle(fontWeight: FontWeight.bold)),
          Text(releaseNotes!),
        ],
        const SizedBox(height: 22),
        if (checking || downloading) const LinearProgressIndicator(),
        const SizedBox(height: 12),
        if (hasUpdate) FilledButton.icon(
          onPressed: downloading ? null : downloadAndInstall,
          icon: const Icon(Icons.download),
          label: const Text('ШИНЭЧЛЭХ'),
          style: FilledButton.styleFrom(backgroundColor: blue, padding: const EdgeInsets.symmetric(vertical: 15)),
        ),
        OutlinedButton.icon(
          onPressed: checking ? null : () => checkUpdate(),
          icon: const Icon(Icons.refresh),
          label: const Text('Дахин шалгах'),
        ),
        const SizedBox(height: 10),
        const Text('Шинэчлэлт суулгах үед Android-ийн баталгаажуулах цонх гарна. Шинэ хувилбар ижил гарын үсгээр гарсан байх шаардлагатай.', style: TextStyle(fontSize: 12, color: Colors.blueGrey)),
      ]),
    );
  }
}


class ProfilePage extends StatefulWidget {
  final String phone;
  const ProfilePage({super.key, required this.phone});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _location = TextEditingController();
  String _role = 'Тэмцээн зохион байгуулагч';
  String _sport = 'Жүдо';
  bool _loading = true;
  bool _saving = false;
  bool _saved = false;

  static const _roles = <String>[
    'Тэмцээн зохион байгуулагч',
    'Шүүгч',
  ];
  static const _sports = <String>[
    'Жүдо', 'Самбо', 'Чөлөөт бөх', 'Үндэсний бөх',
    'Сагсан бөмбөг', 'Волейбол', 'Хөлбөмбөг',
    'Бокс', 'Таеквондо', 'Гимнастик', 'Бусад',
  ];

  String get _keyPrefix => 'arena360.profile.${widget.phone}.';

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _name.text = prefs.getString('${_keyPrefix}name') ?? '';
      _location.text = prefs.getString('${_keyPrefix}location') ?? '';
      final savedRole = prefs.getString('${_keyPrefix}role');
      final savedSport = prefs.getString('${_keyPrefix}sport');
      if (mounted) {
        setState(() {
          if (_roles.contains(savedRole)) _role = savedRole!;
          if (_sports.contains(savedSport)) _sport = savedSport!;
          _loading = false;
          _saved = _name.text.trim().isNotEmpty;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('${_keyPrefix}name', _name.text.trim());
      await prefs.setString('${_keyPrefix}location', _location.text.trim());
      await prefs.setString('${_keyPrefix}role', _role);
      await prefs.setString('${_keyPrefix}sport', _sport);
      if (!mounted) return;
      setState(() {
        _saving = false;
        _saved = true;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Профайл энэ төхөөрөмжид хадгалагдлаа.')),
      );
    } catch (_) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Хадгалж чадсангүй. Дахин оролдоно уу.')),
        );
      }
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _location.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Миний профайл')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [navy, Color(0xFF244B91)],
                    ),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.account_circle, color: Colors.white, size: 42),
                      SizedBox(height: 10),
                      Text(
                        'ARENA 360 PROFILE',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      SizedBox(height: 5),
                      Text(
                        'Өөрийн мэдээлэл болон хэрэглэгчийн төрлөө тохируулна уу.',
                        style: TextStyle(color: Colors.white70),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                if (_saved)
                  Container(
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 14),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEAF7EF),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.check_circle, color: Colors.green),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text('Профайлын мэдээлэл энэ төхөөрөмжид хадгалагдсан.'),
                        ),
                      ],
                    ),
                  ),
                Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextFormField(
                        controller: _name,
                        textCapitalization: TextCapitalization.words,
                        decoration: const InputDecoration(
                          labelText: 'Овог, нэр',
                          prefixIcon: Icon(Icons.person_outline),
                        ),
                        validator: (value) => (value ?? '').trim().isEmpty
                            ? 'Нэрээ оруулна уу'
                            : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: widget.phone,
                        readOnly: true,
                        decoration: const InputDecoration(
                          labelText: 'Бүртгэлтэй утасны дугаар',
                          prefixIcon: Icon(Icons.phone),
                        ),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        value: _role,
                        decoration: const InputDecoration(
                          labelText: 'Хэрэглэгчийн төрөл',
                          prefixIcon: Icon(Icons.badge_outlined),
                        ),
                        items: _roles
                            .map((value) => DropdownMenuItem(
                                  value: value,
                                  child: Text(value),
                                ))
                            .toList(),
                        onChanged: (value) {
                          if (value != null) setState(() => _role = value);
                        },
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        value: _sport,
                        decoration: const InputDecoration(
                          labelText: 'Спортын төрөл',
                          prefixIcon: Icon(Icons.sports),
                        ),
                        items: _sports
                            .map((value) => DropdownMenuItem(
                                  value: value,
                                  child: Text(value),
                                ))
                            .toList(),
                        onChanged: (value) {
                          if (value != null) setState(() => _sport = value);
                        },
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _location,
                        decoration: const InputDecoration(
                          labelText: 'Аймаг / хот, дүүрэг',
                          prefixIcon: Icon(Icons.location_on_outlined),
                        ),
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 52,
                        child: FilledButton.icon(
                          onPressed: _saving ? null : _saveProfile,
                          style: FilledButton.styleFrom(
                            backgroundColor: blue,
                          ),
                          icon: _saving
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.save_outlined),
                          label: Text(_saving ? 'ХАДГАЛЖ БАЙНА...' : 'ПРОФАЙЛ ХАДГАЛАХ'),
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Анхааруулга: энэ шатанд профайл зөвхөн тухайн утсанд хадгалагдана. Серверийн бүртгэл, SMS баталгаажуулалт болон бусад төхөөрөмжтэй синк хараахан холбогдоогүй.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.blueGrey,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
