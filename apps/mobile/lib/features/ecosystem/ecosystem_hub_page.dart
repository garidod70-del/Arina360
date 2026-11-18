import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../core/network/api_client.dart';
import '../../core/widgets/qpay_payment_dialog.dart';

class EcosystemHubPage extends StatelessWidget {
  final bool isAdmin;
  const EcosystemHubPage({super.key, this.isAdmin = false});

  @override
  Widget build(BuildContext context) {
    final items = <_HubItem>[
      _HubItem('QR баталгаажуулалт', Icons.qr_code_2, const QrPassPage()),
      _HubItem('Медаль, онооны хүснэгт', Icons.military_tech, const MedalBoardPage()),
      _HubItem('Клуб, дасгалжуулагч', Icons.groups, const ClubPage()),
      _HubItem('Спорт барааны дэлгүүр', Icons.shopping_bag, const StorePage()),
      _HubItem('Мэдэгдэл, чат', Icons.forum, const MessageCentrePage()),
      _HubItem('Миний орлого', Icons.account_balance_wallet, const ProviderEarningsPage()),
      if (isAdmin) _HubItem('Админ аналитик', Icons.analytics, const AnalyticsPage()),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('ARINA 360 • Нэгдсэн систем')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Color(0xFF211052), Color(0xFF4330A8), Color(0xFF1267C9)]),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [BoxShadow(color: Color(0xFF603BDA).withValues(alpha: .22), blurRadius: 22, offset: Offset(0, 10))],
          ),
          child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('ARINA 360 • SPORT PLATFORM', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w800)),
            SizedBox(height: 8),
            Text('Спортын нэгдсэн удирдлага', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900)),
            SizedBox(height: 6),
            Text('QR • Клуб • Дэлгүүр • Чат • Медаль • Аналитик', style: TextStyle(color: Colors.white70)),
          ]),
        ),
        const SizedBox(height: 16),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: items.length,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12, mainAxisExtent: 152),
          itemBuilder: (context, index) {
            final item = items[index];
            return Card(clipBehavior: Clip.antiAlias, child: InkWell(
              borderRadius: BorderRadius.circular(18),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => item.page)),
              child: Ink(
                decoration: BoxDecoration(
                  gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [Theme.of(context).colorScheme.surface, Theme.of(context).colorScheme.primary.withValues(alpha: .09)]),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(colors: [Color(0xFF873BEE), Color(0xFF268CFF)]),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Icon(item.icon, size: 24, color: Colors.white),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        item.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12),
                      ),
                      const Spacer(),
                      Align(
                        alignment: Alignment.centerRight,
                        child: Icon(Icons.arrow_forward_rounded, size: 18, color: Theme.of(context).colorScheme.secondary),
                      ),
                    ],
                  ),
                ),
              ),
            ));
          },
        ),
      ]),
    );
  }
}

class _HubItem {
  final String title; final IconData icon; final Widget page;
  const _HubItem(this.title, this.icon, this.page);
}

abstract class _EcosystemState<T extends StatefulWidget> extends State<T> {
  final api = ApiClient();
  static const secure = FlutterSecureStorage();
  bool busy = false;
  String? error;
  Future<String> token() async {
    final value = await secure.read(key: 'arena_access_token');
    if (value == null || value.isEmpty) throw Exception('Нэвтрэх эрх олдсонгүй.');
    return value;
  }
  Future<void> work(Future<void> Function(String) action) async {
    setState(() { busy = true; error = null; });
    try { await action(await token()); }
    catch (e) { if (mounted) setState(() => error = e.toString()); }
    finally { if (mounted) setState(() => busy = false); }
  }
  Widget status() => busy ? const LinearProgressIndicator() : error == null ? const SizedBox.shrink() :
    Card(color: Theme.of(context).colorScheme.errorContainer, child: Padding(padding: const EdgeInsets.all(12), child: Text(error!)));
  Map<String, dynamic>? _profileCache;

  Future<Map<String, dynamic>> profile() async {
    if (_profileCache != null) return _profileCache!;
    final accessToken = await token();
    Map<String, dynamic> saved = {};
    Map<String, dynamic> account = {};
    try { saved = await api.get('/profile/me', token: accessToken); } catch (_) {}
    try { account = await api.get('/auth/me', token: accessToken); } catch (_) {}
    _profileCache = {...saved, 'phone': account['phone']};
    return _profileCache!;
  }

  String _profileValue(Map<String, dynamic> profile, String key) {
    final value = switch (key) {
      'contact_phone' || 'phone' => profile['phone'],
      'full_name' || 'name' => profile['full_name'] ?? profile['name'],
      'sport' => profile['sport'],
      'region' => profile['region'],
      'delivery_address' || 'address' => profile['address'] ?? profile['delivery_address'],
      _ => null,
    };
    return value?.toString() ?? '';
  }

  Future<Map<String, dynamic>?> form(String title, List<_Input> inputs, {bool autofillPhone = true}) async {
    final savedProfile = await profile();
    final ctrls = <String, TextEditingController>{};
    final selected = <String, String>{};
    for (final input in inputs) {
      final fromProfile = !autofillPhone && (input.key == 'contact_phone' || input.key == 'phone')
          ? ''
          : _profileValue(savedProfile, input.key);
      final initial = fromProfile.isNotEmpty ? fromProfile : input.initial;
      ctrls[input.key] = TextEditingController(text: initial);
      if (input.options.isNotEmpty) {
        selected[input.key] = input.options.contains(initial) ? initial : input.options.first;
        ctrls[input.key]!.text = selected[input.key]!;
      }
    }
    final result = await showDialog<Map<String, dynamic>>(context: context, builder: (ctx) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: inputs.map((f) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: f.options.isNotEmpty
          ? DropdownButtonFormField<String>(
              value: selected[f.key],
              isExpanded: true,
              decoration: InputDecoration(labelText: f.label),
              items: f.options.map((option) => DropdownMenuItem(value: option, child: Text(option))).toList(),
              onChanged: (value) { if (value != null) { selected[f.key] = value; ctrls[f.key]!.text = value; } },
            )
          : TextField(
              controller: ctrls[f.key],
              keyboardType: f.number ? TextInputType.number : TextInputType.text,
              decoration: InputDecoration(
                labelText: f.label,
                suffixIcon: _profileValue(savedProfile, f.key).isNotEmpty
                  ? const Icon(Icons.verified_user_outlined, size: 18)
                  : null,
              ),
            ),
      )).toList())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('БОЛИХ')),
        FilledButton(onPressed: () {
          final data = <String, dynamic>{};
          for (final f in inputs) {
            final v = ctrls[f.key]!.text.trim();
            data[f.key] = f.number ? int.tryParse(v) ?? 0 : v;
          }
          Navigator.pop(ctx, data);
        }, child: const Text('ХАДГАЛАХ')),
      ],
    ));
    for (final c in ctrls.values) { c.dispose(); }
    return result;
  }
  void toast(String text) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text))); }
  @override void dispose() { api.close(); super.dispose(); }
}

class _Input {
  final String key, label, initial;
  final bool number;
  final List<String> options;
  const _Input(this.key, this.label, {this.initial = '', this.number = false, this.options = const []});
}

class QrPassPage extends StatefulWidget {
  const QrPassPage({super.key});
  @override State<QrPassPage> createState() => _QrPassPageState();
}
class _QrPassPageState extends _EcosystemState<QrPassPage> {
  String? code;
  final verifyInput = TextEditingController();
  @override void dispose() { verifyInput.dispose(); super.dispose(); }
  Future<void> issue() async {
    final data = await form('QR эрх үүсгэх', const [
      _Input('purpose', 'Зориулалт', initial: 'event_entry', options: ['event_entry', 'course_attendance', 'fitness_checkin']),
      _Input('reference_type', 'Холбоосын төрөл', initial: 'fitness_pass', options: ['fitness_pass', 'competition', 'club']),
      _Input('reference_id', 'Холбоосын ID', initial: '1', number: true),
      _Input('expires_in_minutes', 'Хүчинтэй минут', initial: '60', number: true),
    ]);
    if (data == null) return;
    await work((t) async {
      final result = await api.postAuthorized('/qr/passes', token: t, body: data);
      if (mounted) setState(() => code = result['token'].toString());
    });
  }
  Future<void> scan() async {
    final value = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => Scaffold(
        appBar: AppBar(title: const Text('QR уншуулах')),
        body: MobileScanner(onDetect: (capture) {
          final raw = capture.barcodes.isNotEmpty ? capture.barcodes.first.rawValue : null;
          if (raw != null && raw.isNotEmpty && Navigator.of(context).canPop()) {
            Navigator.of(context).pop(raw);
          }
        }),
      )),
    );
    if (value != null && mounted) {
      verifyInput.text = value;
      await verify();
    }
  }
  Future<void> verify() async {
    if (verifyInput.text.trim().isEmpty) return;
    await work((t) async {
      await api.postAuthorized('/qr/verify', token: t, body: {'token': verifyInput.text.trim()});
      verifyInput.clear(); toast('QR амжилттай баталгаажлаа.');
    });
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('QR баталгаажуулалт')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(),
      Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(children: [
        const Icon(Icons.qr_code_2, size: 44),
        const Text('ХУГАЦААТАЙ НЭГ УДААГИЙН QR', style: TextStyle(fontWeight: FontWeight.w900)),
        FilledButton.icon(onPressed: busy ? null : issue, icon: const Icon(Icons.add), label: const Text('QR ҮҮСГЭХ')),
        if (code != null) QrImageView(data: code!, size: 220, backgroundColor: Colors.white),
        if (code != null) SelectableText(code!, textAlign: TextAlign.center),
      ]))),
      Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(children: [
        TextField(controller: verifyInput, decoration: const InputDecoration(labelText: 'QR токен оруулах')),
        const SizedBox(height: 8),
        OutlinedButton.icon(onPressed: busy ? null : scan, icon: const Icon(Icons.camera_alt), label: const Text('КАМЕРААР УНШУУЛАХ')),
        OutlinedButton.icon(onPressed: busy ? null : verify, icon: const Icon(Icons.verified), label: const Text('БАТАЛГААЖУУЛАХ')),
        const Text('QR кодыг камераар уншуулж, сервер дээр нэг удаа баталгаажуулна.', style: TextStyle(fontSize: 11, color: Colors.blueGrey)),
      ]))),
    ]),
  );
}

class MedalBoardPage extends StatefulWidget {
  const MedalBoardPage({super.key});
  @override State<MedalBoardPage> createState() => _MedalBoardPageState();
}
class _MedalBoardPageState extends _EcosystemState<MedalBoardPage> {
  List<Map<String, dynamic>> rows = [];
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async { rows = await api.getList('/leaderboards/medals', token: t); if (mounted) setState(() {}); });
  Future<void> award() async {
    final data = await form('Медаль бүртгэх', const [
      _Input('tournament_id', 'Тэмцээний ID', initial: '1', number: true),
      _Input('participant_id', 'Тамирчны ID', initial: '1', number: true),
      _Input('medal', 'Медалийн төрөл', initial: 'gold', options: ['gold', 'silver', 'bronze']),
      _Input('points', 'Оноо', initial: '10', number: true),
    ]);
    if (data == null) return;
    await work((t) async {
      final id = data.remove('tournament_id');
      await api.postAuthorized('/competitions/' + id.toString() + '/medals', token: t, body: data);
      rows = await api.getList('/leaderboards/medals', token: t);
      if (mounted) setState(() {}); toast('Медаль бүртгэгдлээ.');
    });
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Медаль, онооны хүснэгт'), actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))]),
    floatingActionButton: FloatingActionButton.extended(onPressed: busy ? null : award, icon: const Icon(Icons.add), label: const Text('МЕДАЛЬ')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(), const Text('КЛУБЫН МЕДАЛИЙН ЧАНСАА', style: TextStyle(fontWeight: FontWeight.w900)),
      ...rows.asMap().entries.map((e) => Card(child: ListTile(
        leading: CircleAvatar(child: Text((e.key + 1).toString())),
        title: Text(e.value['club']?.toString() ?? 'Клуб'),
        subtitle: Text('Алт ' + e.value['gold'].toString() + ' • Мөнгө ' + e.value['silver'].toString() + ' • Хүрэл ' + e.value['bronze'].toString()),
        trailing: Text(e.value['points'].toString() + ' оноо'),
      ))),
    ]),
  );
}

class ClubPage extends StatefulWidget {
  const ClubPage({super.key});
  @override State<ClubPage> createState() => _ClubPageState();
}
class _ClubPageState extends _EcosystemState<ClubPage> {
  List<Map<String, dynamic>> clubs = [];
  List<Map<String, dynamic>> mine = [];
  List<Map<String, dynamic>> coaches = [];
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async {
    clubs = await api.getList('/clubs', token: t);
    mine = await api.getList('/clubs/mine', token: t);
    coaches = await api.getList('/coaches', token: t);
    if (mounted) setState(() {});
  });
  Future<void> manageClub(int id) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ClubMembersPage(clubId: id)));
    await refresh();
  }
  Future<void> createClub() async {
    final data = await form('Клуб үүсгэх', const [
      _Input('name', 'Клубын нэр'), _Input('sport', 'Спортын төрөл', initial: 'Жүдо', options: ['Жүдо', 'Самбо', 'Чөлөөт бөх', 'Үндэсний бөх', 'Бокс', 'Волейбол', 'Сагсан бөмбөг', 'Хөл бөмбөг', 'Таеквондо', 'Каратэ', 'Гимнастик', 'Бусад']),
      _Input('region', 'Аймаг / хот'), _Input('description', 'Тайлбар'),
      _Input('contact_phone', 'Утас'), _Input('membership_fee', 'Гишүүнчлэлийн үнэ ₮', initial: '0', number: true),
    ]);
    if (data == null) return;
    await work((t) async {
      await api.postAuthorized('/clubs', token: t, body: data);
      mine = await api.getList('/clubs/mine', token: t);
      if (mounted) setState(() {});
      toast('Клубын бүртгэл үүслээ. Админ баталгаажуулалт хүлээнэ.');
    });
  }
  Future<void> coach() async {
    final data = await form('Дасгалжуулагчийн профайл', const [
      _Input('club_id', 'Клубын ID (0 бол байхгүй)', initial: '0', number: true),
      _Input('sport', 'Спортын төрөл', initial: 'Жүдо', options: ['Жүдо', 'Самбо', 'Чөлөөт бөх', 'Үндэсний бөх', 'Бокс', 'Волейбол', 'Сагсан бөмбөг', 'Хөл бөмбөг', 'Таеквондо', 'Каратэ', 'Гимнастик', 'Бусад']), _Input('qualification', 'Мэргэжлийн үнэмлэх'),
      _Input('experience_years', 'Ажилласан жил', initial: '0', number: true),
      _Input('specialties', 'Мэргэшсэн чиглэл'),
    ]);
    if (data == null) return;
    if (data['club_id'] == 0) data['club_id'] = null;
    await work((t) async { await api.postAuthorized('/coaches/profile', token: t, body: data); toast('Дасгалжуулагчийн мэдээлэл хадгалагдлаа.'); });
  }
  Future<void> join(int id) async => work((t) async {
    final membership = await api.postAuthorized('/clubs/' + id.toString() + '/join', token: t, body: {});
    if (membership['status'] == 'pending_payment') {
      await QPayPaymentDialog.open(
        context: context, api: api, token: t, orderType: 'club_membership',
        orderId: membership['id'] as int,
        onPaid: () { toast('Клубын гишүүнчлэлийн төлбөр баталгаажлаа.'); refresh(); },
      );
    } else {
      toast('Үнэгүй клубын элсэх хүсэлт илгээгдлээ.');
    }
    await refresh();
  });
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Клуб, дасгалжуулагч'), actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))]),
    floatingActionButton: Column(mainAxisSize: MainAxisSize.min, children: [
      FloatingActionButton.small(heroTag: 'coach', onPressed: coach, child: const Icon(Icons.school)),
      const SizedBox(height: 8),
      FloatingActionButton.extended(heroTag: 'club', onPressed: createClub, icon: const Icon(Icons.add), label: const Text('КЛУБ')),
    ]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(),
      const Text('БАТАЛГААЖСАН КЛУБУУД', style: TextStyle(fontWeight: FontWeight.w900)),
      ...clubs.map((x) => Card(child: ListTile(
        leading: const Icon(Icons.groups), title: Text(x['name'].toString()),
        subtitle: Text(x['sport'].toString() + ' • ' + x['region'].toString() + ' • Гишүүнчлэл: ' + (x['membership_fee'] ?? 0).toString() + ' ₮'),
        trailing: TextButton(onPressed: busy ? null : () => join(x['id'] as int), child: const Text('ЭЛСЭХ')),
      ))),
      const SizedBox(height: 12),
      const Text('МИНИЙ КЛУБУУД', style: TextStyle(fontWeight: FontWeight.w900)),
      ...mine.map((x) => Card(child: ListTile(
        leading: const Icon(Icons.shield_outlined), title: Text(x['name'].toString()),
        subtitle: Text('Төлөв: ' + x['verification_status'].toString()),
        trailing: IconButton(onPressed: busy ? null : () => manageClub(x['id'] as int), icon: const Icon(Icons.manage_accounts)),
      ))),
      const SizedBox(height: 12),
      const Text('БАТАЛГААЖСАН ДАСГАЛЖУУЛАГЧИД', style: TextStyle(fontWeight: FontWeight.w900)),
      ...coaches.map((x) => Card(child: ListTile(
        leading: const Icon(Icons.school), title: Text(x['sport'].toString()),
        subtitle: Text(x['qualification'].toString() + ' • ' + x['experience_years'].toString() + ' жил'),
      ))),
    ]),
  );
}

class StorePage extends StatefulWidget {
  const StorePage({super.key});
  @override State<StorePage> createState() => _StorePageState();
}
class _StorePageState extends _EcosystemState<StorePage> {
  List<Map<String, dynamic>> products = [];
  List<Map<String, dynamic>> orders = [];
  Map<String, dynamic> cart = {};
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async {
    products = await api.getList('/store/products', token: t);
    cart = await api.get('/store/cart', token: t);
    orders = await api.getList('/store/orders', token: t);
    if (mounted) setState(() {});
  });
  Future<void> addProduct() async {
    final data = await form('Бараа нэмэх', const [
      _Input('title', 'Барааны нэр'), _Input('description', 'Тайлбар'),
      _Input('category', 'Ангилал', options: ['Хувцас', 'Гутал', 'Бээлий, хамгаалалт', 'Бэлтгэлийн хэрэгсэл', 'Жин, сэргээх хэрэгсэл', 'Бусад']),
      _Input('price', 'Үнэ ₮', number: true), _Input('stock', 'Үлдэгдэл', number: true),
    ]);
    if (data == null) return;
    await work((t) async { await api.postAuthorized('/store/products', token: t, body: data); await refresh(); });
  }
  Future<void> addCart(int id) async => work((t) async {
    await api.postAuthorized('/store/cart', token: t, body: {'product_id': id, 'quantity': 1});
    cart = await api.get('/store/cart', token: t);
    if (mounted) setState(() {});
    toast('Сагсанд нэмэгдлээ.');
  });
  Future<void> payOrder(int id, {String? tokenValue, bool refreshAfter = true}) async {
    try {
      final accessToken = tokenValue ?? await token();
      await QPayPaymentDialog.open(
        context: context, api: api, token: accessToken,
        orderType: 'store_order', orderId: id,
        onPaid: () => toast('Төлбөр баталгаажлаа. Дэлгүүрт захиалгын мэдэгдэл очлоо.'),
      );
      if (refreshAfter) await refresh();
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }
  Future<void> checkout() async {
    final data = await form(
      'Хүргэлтийн хаяг',
      const [_Input('delivery_address', 'Хүргэлтийн хаяг')],
      autofillPhone: false,
    );
    if (data == null) return;
    await work((t) async {
      final order = await api.postAuthorized('/store/checkout', token: t, body: data);
      if (order['payment_status'] == 'free') {
        toast('Үнэгүй захиалга бүртгэгдлээ. Дэлгүүрт мэдэгдэл очлоо.');
      } else {
        await payOrder(order['id'] as int, tokenValue: t, refreshAfter: false);
      }
      products = await api.getList('/store/products', token: t);
      cart = await api.get('/store/cart', token: t);
      orders = await api.getList('/store/orders', token: t);
      if (mounted) setState(() {});
    });
  }
  String _orderStatus(Map<String, dynamic> order) {
    if (order['payment_status'] == 'paid') return 'Төлбөр төлөгдсөн';
    if (order['payment_status'] == 'free') return 'Үнэгүй захиалга';
    return 'Төлбөр хүлээгдэж байна';
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Спорт барааны дэлгүүр'), actions: [IconButton(onPressed: busy ? null : refresh, icon: const Icon(Icons.refresh))]),
    floatingActionButton: FloatingActionButton.extended(onPressed: busy ? null : addProduct, icon: const Icon(Icons.add), label: const Text('БАРАА НЭМЭХ')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(),
      Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(children: [
        Text('Сагсны дүн: ${cart['total_amount'] ?? 0} ₮'),
        FilledButton(onPressed: busy || (cart['items'] as List? ?? []).isEmpty ? null : checkout, child: const Text('ЗАХИАЛГА ҮҮСГЭХ')),
      ]))),
      const Text('МИНИЙ ЗАХИАЛГУУД', style: TextStyle(fontWeight: FontWeight.w900)),
      ...orders.map((order) => Card(child: ListTile(
        title: Text('Захиалга #${order['id']} • ${order['total_amount']} ₮'),
        subtitle: Text('${_orderStatus(order)} • ${order['status']}'),
        trailing: order['payment_status'] == 'unpaid' && order['status'] == 'pending_payment'
            ? TextButton(onPressed: busy ? null : () => payOrder(order['id'] as int), child: const Text('ТӨЛӨХ'))
            : const Icon(Icons.check_circle_outline),
      ))),
      const SizedBox(height: 8),
      const Text('БАРААНУУД', style: TextStyle(fontWeight: FontWeight.w900)),
      ...products.map((x) => Card(child: ListTile(
        title: Text(x['title'].toString()),
        subtitle: Text(x['category'].toString() + ' • Үлдэгдэл ' + x['stock'].toString()),
        trailing: TextButton(onPressed: busy ? null : () => addCart(x['id'] as int), child: Text(x['price'].toString() + ' ₮ +')),
      ))),
    ]),
  );
}

class MessageCentrePage extends StatefulWidget {
  const MessageCentrePage({super.key});
  @override State<MessageCentrePage> createState() => _MessageCentrePageState();
}
class _MessageCentrePageState extends _EcosystemState<MessageCentrePage> {
  List<Map<String, dynamic>> notes = [];
  List<Map<String, dynamic>> chats = [];
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async {
    notes = await api.getList('/notifications', token: t); chats = await api.getList('/chat/conversations', token: t); if (mounted) setState(() {});
  });
  Future<void> startChat() async {
    final data = await form('Чат эхлүүлэх', const [_Input('other_user_id', 'Хэрэглэгчийн ID', number: true)]);
    if (data == null) return;
    await work((t) async {
      final result = await api.postAuthorized('/chat/conversations', token: t, body: data);
      toast('Чат үүслээ. ID: ' + result['id'].toString());
      chats = await api.getList('/chat/conversations', token: t); if (mounted) setState(() {});
    });
  }
  Future<void> read(int id) async => work((t) async {
    await api.postAuthorized('/notifications/' + id.toString() + '/read', token: t, body: {});
    notes = await api.getList('/notifications', token: t); if (mounted) setState(() {});
  });
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Мэдэгдэл, чат'), actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))]),
    floatingActionButton: FloatingActionButton.extended(onPressed: startChat, icon: const Icon(Icons.chat), label: const Text('ЧАТ ЭХЛҮҮЛЭХ')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(), const Text('МЭДЭГДЭЛ', style: TextStyle(fontWeight: FontWeight.w900)),
      ...notes.map((x) => Card(child: ListTile(
        title: Text(x['title'].toString()), subtitle: Text(x['body'].toString()),
        trailing: x['is_read'] == true ? const Icon(Icons.check) : IconButton(onPressed: () => read(x['id'] as int), icon: const Icon(Icons.done)),
      ))),
      const SizedBox(height: 12), const Text('ЧАТ', style: TextStyle(fontWeight: FontWeight.w900)),
      ...chats.map((x) => Card(child: ListTile(
        leading: const Icon(Icons.person), title: Text('Хэрэглэгч #' + x['other_user_id'].toString()),
        subtitle: Text(x['last_message']?.toString() ?? 'Шинэ харилцан яриа'),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => ChatThreadPage(conversationId: x['id'] as int))),
      ))),
    ]),
  );
}

class AnalyticsPage extends StatefulWidget {
  const AnalyticsPage({super.key});
  @override State<AnalyticsPage> createState() => _AnalyticsPageState();
}
class _AnalyticsPageState extends _EcosystemState<AnalyticsPage> {
  Map<String, dynamic> stats = {};
  Map<String, dynamic> paymentStats = {};
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async {
    stats = await api.get('/admin/analytics', token: t);
    paymentStats = await api.get('/payments/admin/summary', token: t);
    if (mounted) setState(() {});
  });
  Widget _metric(String label, dynamic value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [
      Expanded(child: Text(label)),
      Text((value ?? 0).toString() + ' ₮', style: const TextStyle(fontWeight: FontWeight.w800)),
    ]),
  );
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Админ аналитик'), actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(),
      Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('ТӨЛБӨРИЙН ОРЛОГО • 5% ШИМТГЭЛ', style: TextStyle(fontWeight: FontWeight.w900)),
        const SizedBox(height: 10),
        _metric('Нийт төлөгдсөн', paymentStats['gross_paid_mnt']),
        _metric('ARENA 360 шимтгэл', paymentStats['platform_commission_mnt']),
        _metric('Үйлчилгээ үзүүлэгчид', paymentStats['provider_net_after_refunds_mnt']),
        _metric('Буцаалт', paymentStats['refunded_mnt']),
        ListTile(dense: true, title: const Text('Төлбөр хүлээгдэж буй нэхэмжлэл'), trailing: Text((paymentStats['pending_invoices'] ?? 0).toString())),
        ListTile(dense: true, title: const Text('Төлбөр хүлээгдэж буй захиалга'), trailing: Text((paymentStats['pending_orders_total'] ?? 0).toString())),
      ]))),
      if (paymentStats['categories'] is Map)
        ...((paymentStats['categories'] as Map).entries.map((entry) => Card(
          child: ExpansionTile(
            title: Text(entry.key.toString()),
            subtitle: Text('Шимтгэл: ${entry.value['commission']} ₮'),
            children: [
              ListTile(title: const Text('Нийт төлбөр'), trailing: Text('${entry.value['gross']} ₮')),
              ListTile(title: const Text('Үйлчилгээ үзүүлэгчийн орлого'), trailing: Text('${entry.value['provider_net']} ₮')),
              ListTile(title: const Text('Буцаалт'), trailing: Text('${entry.value['refund']} ₮')),
            ],
          ),
        ))),
    ]),
  );
}


class ChatThreadPage extends StatefulWidget {
  final int conversationId;
  const ChatThreadPage({super.key, required this.conversationId});
  @override State<ChatThreadPage> createState() => _ChatThreadPageState();
}

class _ChatThreadPageState extends _EcosystemState<ChatThreadPage> {
  final controller = TextEditingController();
  List<Map<String, dynamic>> messages = [];
  @override void initState() { super.initState(); refresh(); }
  @override void dispose() { controller.dispose(); super.dispose(); }
  Future<void> refresh() async => work((t) async {
    messages = await api.getList('/chat/conversations/' + widget.conversationId.toString() + '/messages', token: t);
    if (mounted) setState(() {});
  });
  Future<void> send() async {
    final body = controller.text.trim();
    if (body.isEmpty) return;
    await work((t) async {
      await api.postAuthorized('/chat/conversations/' + widget.conversationId.toString() + '/messages',
        token: t, body: {'body': body});
      controller.clear();
      messages = await api.getList('/chat/conversations/' + widget.conversationId.toString() + '/messages', token: t);
      if (mounted) setState(() {});
    });
  }
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Харилцан яриа'), actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))]),
    body: Column(children: [
      status(),
      Expanded(child: ListView(padding: const EdgeInsets.all(12), children: messages.map((x) => Align(
        alignment: Alignment.centerLeft,
        child: Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(x['body'].toString()))),
      )).toList())),
      SafeArea(child: Padding(padding: const EdgeInsets.all(10), child: Row(children: [
        Expanded(child: TextField(controller: controller, decoration: const InputDecoration(hintText: 'Зурвас бичих'))),
        IconButton(onPressed: busy ? null : send, icon: const Icon(Icons.send)),
      ]))),
    ]),
  );
}


class ClubMembersPage extends StatefulWidget {
  final int clubId;
  const ClubMembersPage({super.key, required this.clubId});
  @override State<ClubMembersPage> createState() => _ClubMembersPageState();
}

class _ClubMembersPageState extends _EcosystemState<ClubMembersPage> {
  List<Map<String, dynamic>> members = [];
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async {
    members = await api.getList('/clubs/' + widget.clubId.toString() + '/members', token: t);
    if (mounted) setState(() {});
  });
  Future<void> decide(int id, bool accepted) async => work((t) async {
    await api.postAuthorized('/clubs/' + widget.clubId.toString() + '/members/' + id.toString() + '/decision',
      token: t, body: {'accepted': accepted});
    members = await api.getList('/clubs/' + widget.clubId.toString() + '/members', token: t);
    if (mounted) setState(() {});
  });
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Клубын гишүүд'), actions: [IconButton(onPressed: refresh, icon: const Icon(Icons.refresh))]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(),
      ...members.map((x) => Card(child: ListTile(
        title: Text('Хэрэглэгч #' + x['user_id'].toString()),
        subtitle: Text(x['role'].toString() + ' • ' + x['status'].toString()),
        trailing: x['status'] == 'pending' ? Wrap(children: [
          IconButton(onPressed: busy ? null : () => decide(x['id'] as int, true), icon: const Icon(Icons.check, color: Colors.green)),
          IconButton(onPressed: busy ? null : () => decide(x['id'] as int, false), icon: const Icon(Icons.close, color: Colors.red)),
        ]) : null,
      ))),
    ]),
  );
}


class ProviderEarningsPage extends StatefulWidget {
  const ProviderEarningsPage({super.key});
  @override State<ProviderEarningsPage> createState() => _ProviderEarningsPageState();
}
class _ProviderEarningsPageState extends _EcosystemState<ProviderEarningsPage> {
  Map<String, dynamic> summary = {};
  @override void initState() { super.initState(); refresh(); }
  Future<void> refresh() async => work((t) async {
    summary = await api.get('/payments/provider/summary', token: t);
    if (mounted) setState(() {});
  });
  Widget _metric(String title, dynamic value) => ListTile(
    dense: true,
    title: Text(title),
    trailing: Text('${value ?? 0} ₮', style: const TextStyle(fontWeight: FontWeight.w800)),
  );
  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Миний үйлчилгээний орлого'), actions: [
      IconButton(onPressed: busy ? null : refresh, icon: const Icon(Icons.refresh)),
    ]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      status(),
      Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('ОРЛОГЫН ТАЙЛАН', style: TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          _metric('Нийт төлөгдсөн захиалга', summary['gross_paid_mnt']),
          _metric('ARENA 360 шимтгэл (5%)', summary['commission_deducted_mnt']),
          _metric('Буцаалт', summary['refunds_mnt']),
          const Divider(),
          _metric('Танд ногдох цэвэр орлого', summary['net_after_commission_and_refunds_mnt']),
          ListTile(dense: true, title: const Text('Гүйлгээний тоо'), trailing: Text((summary['transactions'] ?? 0).toString(), style: const TextStyle(fontWeight: FontWeight.w800))),
        ],
      ))),
      const Text('СҮҮЛИЙН ГҮЙЛГЭЭ', style: TextStyle(fontWeight: FontWeight.w900)),
      ...((summary['recent_transactions'] as List? ?? []).map((entry) => Card(child: ListTile(
        title: Text('${entry['category']} • №${entry['order_id']}'),
        subtitle: Text('Нийт ${entry['gross_mnt']} ₮ • Шимтгэл ${entry['commission_mnt']} ₮'),
        trailing: Text('${entry['net_mnt']} ₮', style: const TextStyle(fontWeight: FontWeight.w900)),
      )))),
      const Text('Тайлбар: Энэ тайлан нь QPay-ээр баталгаажсан гүйлгээ болон шимтгэлийн бүртгэлийг харуулна. Банкны данс руу бодитоор шилжүүлсэн төлбөрийн түүх биш.', style: TextStyle(fontSize: 12, color: Colors.blueGrey)),
    ]),
  );
}
