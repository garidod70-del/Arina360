import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/config/api_config.dart';
import '../../../core/network/api_client.dart';
import '../domain/service_item.dart';

class ServiceMarketplacePage extends StatefulWidget {
  final ServiceItem service;

  const ServiceMarketplacePage({super.key, required this.service});

  @override
  State<ServiceMarketplacePage> createState() => _ServiceMarketplacePageState();
}

class _ServiceMarketplacePageState extends State<ServiceMarketplacePage> {
  static const _storage = FlutterSecureStorage();
  final ApiClient _api = ApiClient();
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _regionController = TextEditingController();

  List<Map<String, dynamic>> _providers = [];
  List<Map<String, dynamic>> _requests = [];
  int? _currentUserId;
  Map<String, dynamic> _profile = {};
  static const _sportOptions = <String>['Жүдо', 'Самбо', 'Чөлөөт бөх', 'Үндэсний бөх', 'Бокс', 'Волейбол', 'Сагсан бөмбөг', 'Хөл бөмбөг', 'Таеквондо', 'Каратэ', 'Гимнастик', 'Бусад'];
  bool _loading = false;
  bool _saving = false;
  String? _error;

  static const Map<String, String> _categorySlugs = {
    'Дасгалжуулагч': 'coach',
    'Спортын эмч': 'sports_doctor',
    'Хүчний мэргэжилтэн': 'strength_specialist',
    'Сэтгэл зүйч': 'sports_psychologist',
    'Хоол зүйч': 'sports_nutritionist',
    'Хөдөлгөөн засалч': 'physiotherapist',
    'Спортын шинжээч': 'sports_analyst',
    'Заал захиалга': 'venue_booking',
    'Спорт бараа худалдаа': 'sports_store',
    'Сургалт, клубууд': 'clubs_training',
  };

  static const Map<String, String> _requestPrompts = {
    'coach': 'Ямар төрлийн бэлтгэл, ямар зорилготой байгаагаа бичнэ үү.',
    'sports_doctor': 'Үзлэгийн зорилго, хүсэж буй цаг болон шаардлагатай мэдээллээ бичнэ үү.',
    'strength_specialist': 'Хүч, хурд, тэсрэлттэй хүчний аль чиглэлээр ажиллахыг хүсэж байгаагаа бичнэ үү.',
    'sports_psychologist': 'Зөвлөгөөний чиглэл, уулзалтын хэлбэрийн хүсэлтээ бичнэ үү.',
    'sports_nutritionist': 'Хооллолтын зорилго, зөвлөгөө авах чиглэлээ бичнэ үү.',
    'physiotherapist': 'Хөдөлгөөн засал, нөхөн сэргээх үйлчилгээний зорилгоо бичнэ үү.',
    'sports_analyst': 'Ямар тамирчин, баг эсвэл үзүүлэлтэд шинжилгээ хийлгэхээ бичнэ үү.',
    'venue_booking': 'Спортын төрөл, талбайн хэмжээ, ашиглах хугацаа болон шаардлагатай тоноглолыг бичнэ үү.',
    'sports_store': 'Хайж буй бараа, төрөл, хэмжээ, тоо ширхэгийн мэдээллээ бичнэ үү.',
    'clubs_training': 'Элсэх насны ангилал, спортын төрөл, сургалтын түвшнээ бичнэ үү.',
  };

  String get _category => _categorySlugs[widget.service.name] ?? 'coach';

  static const Map<String, List<String>> _requestExtraFields = {
    'coach': ['Тамирчны насны ангилал', 'Бэлтгэлийн зорилго', '7 хоногт бэлтгэл хийх давтамж', 'Ганцаарчилсан эсвэл багийн бэлтгэл'],
    'sports_doctor': ['Үзлэгийн төрөл', 'Цаг авах хэлбэр (биеэр / цахим)', 'Хүссэн үзлэгийн өдөр'],
    'strength_specialist': ['Хөгжүүлэх чадвар (хүч / хурд / тэсрэлт)', 'Тамирчны түвшин', 'Бэлтгэлийн орчин'],
    'sports_psychologist': ['Уулзалтын хэлбэр (биеэр / цахим)', 'Уулзалтын боломжит давтамж'],
    'sports_nutritionist': ['Спортын төрөл, жингийн ангилал', 'Зорилго (жин барих / тэмцээнд бэлтгэх / ерөнхий хооллолт)', 'Хооллолтын зөвлөгөөний хэлбэр'],
    'physiotherapist': ['Үйлчилгээний төрөл', 'Сэргээн засах уулзалтын хэлбэр', 'Хүссэн уулзалтын давтамж'],
    'sports_analyst': ['Тамирчин эсвэл багийн нэр', 'Шинжилгээний төрөл (техник / тактик / статистик)', 'Видео эсвэл материал байгаа эсэх'],
    'sports_store': ['Барааны нэр / загвар', 'Хэмжээ / өнгө', 'Тоо ширхэг', 'Хүргэлтийн байршил'],
    'clubs_training': ['Насны ангилал', 'Бэлтгэлийн түвшин (анхан / дунд / ахисан)', 'Сонирхож буй хуваарь'],
  };

  static const Map<String, List<String>> _providerExtraFields = {
    'coach': ['Заадаг насны ангилал', 'Бэлтгэлийн чиглэл', 'Бэлтгэлийн хуваарь'],
    'sports_doctor': ['Мэргэшил', 'Үзлэгийн чиглэл', 'Цаг авах боломж'],
    'strength_specialist': ['Үнэлгээ, тестийн чиглэл', 'Ашиглах тоног төхөөрөмж', 'Хөтөлбөрийн төрөл'],
    'sports_psychologist': ['Мэргэшлийн чиглэл', 'Зөвлөгөөний хэлбэр', 'Ажиллах цагийн хуваарь'],
    'sports_nutritionist': ['Спортын хоол зүйн чиглэл', 'Зөвлөгөөний хэлбэр', 'Хяналт, дагалтын боломж'],
    'physiotherapist': ['Нөхөн сэргээх чиглэл', 'Ашиглах арга, тоноглол', 'Сеанс үргэлжлэх хугацаа'],
    'sports_analyst': ['Шинжилгээний чиглэл', 'Ашиглах программ, аргачлал', 'Тайлангийн төрөл'],
    'sports_store': ['Барааны ангилал', 'Брэнд / нийлүүлэлт', 'Хүргэлт, солилцооны нөхцөл'],
    'clubs_training': ['Насны ангилал', 'Сургалтын түвшин', 'Долоо хоногийн хуваарь', 'Элсэлтийн нөхцөл'],
  };

  List<String> get _requestFields => _requestExtraFields[_category] ?? const [];
  List<String> get _providerFields => _providerExtraFields[_category] ?? const [];

  String get _moduleWorkflow {
    switch (_category) {
      case 'coach': return 'Дасгалжуулагчийн профайл • бэлтгэлийн чиглэл • насны ангилал • хувийн болон багийн хүсэлт';
      case 'sports_doctor': return 'Эмчийн мэргэшил • үзлэгийн цаг хүсэх • цаг баталгаажуулах • үйлчилгээний түүх';
      case 'strength_specialist': return 'Хүчний үнэлгээ • бэлтгэлийн чиглэл • хөтөлбөрийн хүсэлт • ахицын хяналт';
      case 'sports_psychologist': return 'Мэргэжлийн профайл • нууцлалтай цаг хүсэх • уулзалтын хуваарь';
      case 'sports_nutritionist': return 'Хоол зүйн профайл • зорилгын үнэлгээ • зөвлөгөөний хүсэлт • дагалт';
      case 'physiotherapist': return 'Нөхөн сэргээх чиглэл • үзлэгийн хүсэлт • сеансын хуваарь • явцын хяналт';
      case 'sports_analyst': return 'Тамирчин, багийн шинжилгээ • статистик • видео материал • тайлангийн хүсэлт';
      case 'sports_store': return 'Барааны төрөл • хэмжээ, тоо ширхэг • захиалгын хүсэлт • хүргэлтийн мэдээлэл';
      case 'clubs_training': return 'Клубын профайл • насны ангилал • сургалтын хуваарь • элсэлтийн хүсэлт';
      default: return widget.service.description;
    }
  }

  String get _requestTitleLabel {
    switch (_category) {
      case 'venue_booking':
        return 'Заал / талбай захиалах хүсэлт';
      case 'sports_store':
        return 'Барааны захиалгын хүсэлт';
      case 'clubs_training':
        return 'Клуб, сургалтад элсэх хүсэлт';
      case 'sports_doctor':
        return 'Эмчийн үзлэгийн хүсэлт';
      case 'coach':
        return 'Дасгалжуулалтын хүсэлт';
      default:
        return '${widget.service.name}-ийн үйлчилгээ хүсэх';
    }
  }

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _api.close();
    _searchController.dispose();
    _regionController.dispose();
    super.dispose();
  }

  Future<String?> _readToken() {
    return _storage.read(key: 'arena_access_token');
  }

  Future<void> _loadData() async {
    if (!ApiConfig.isConfigured) {
      setState(() {
        _error = 'Серверийн холболт хараахан тохируулагдаагүй байна. Энэ цэсний бодит бүртгэл, захиалгыг ашиглахын тулд HTTPS API холболт шаардлагатай.';
        _providers = [];
        _requests = [];
      });
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await _readToken();
      if (token == null || token.isEmpty) {
        throw const ApiException(401, 'Нэвтрэх эрх олдсонгүй. Дахин нэвтэрнэ үү.');
      }

      final query = <String, String>{
        'category': _category,
        if (_searchController.text.trim().isNotEmpty)
          'search': _searchController.text.trim(),
        if (_regionController.text.trim().isNotEmpty)
          'region': _regionController.text.trim(),
      };

      final providers = await _api.getList(
        '/services/providers?${Uri(queryParameters: query).query}',
        token: token,
      );
      final requests = await _api.getList('/services/requests/me', token: token);
      final results = await Future.wait([
        _api.get('/auth/me', token: token),
        _api.get('/profile/me', token: token),
      ]);
      final currentUser = results[0];
      final profile = results[1];

      if (!mounted) return;

      setState(() {
        _providers = providers;
        _requests = requests;
        _currentUserId = currentUser['id'] as int?;
        _profile = profile;
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _showRequestForm(Map<String, dynamic> provider) async {
    final formKey = GlobalKey<FormState>();
    final title = TextEditingController(text: _requestTitleLabel);
    final details = TextEditingController();
    final savedSport = _profile['sport']?.toString() ?? '';
    final sport = TextEditingController(text: _sportOptions.contains(savedSport) ? savedSport : '');
    final region = TextEditingController(text: _profile['region']?.toString().isNotEmpty == true ? _profile['region'].toString() : _regionController.text.trim());
    final phone = TextEditingController(text: _profile['phone']?.toString() ?? '');
    final preferredDate = TextEditingController();
    final extraValues = {for (final label in _requestFields) label: TextEditingController()};

    final submitted = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(widget.service.name + ' хүсэлт'),
        content: SizedBox(
          width: 420,
          child: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: title,
                    decoration: const InputDecoration(labelText: 'Хүсэлтийн гарчиг'),
                    validator: (value) => (value ?? '').trim().length < 3
                        ? 'Гарчгаа 3-аас дээш тэмдэгтээр оруулна уу.'
                        : null,
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: details,
                    minLines: 3,
                    maxLines: 5,
                    decoration: InputDecoration(
                      labelText: 'Дэлгэрэнгүй хүсэлт',
                      hintText: _requestPrompts[_category],
                    ),
                    validator: (value) => (value ?? '').trim().length < 5
                        ? 'Хүсэлтээ дэлгэрэнгүй бичнэ үү.'
                        : null,
                  ),
                  ...extraValues.entries.map((entry) => Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: TextFormField(
                      controller: entry.value,
                      decoration: InputDecoration(labelText: entry.key),
                    ),
                  )),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    value: _sportOptions.contains(sport.text) ? sport.text : null,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Спортын төрөл (сонгох)'),
                    items: _sportOptions.map((value) => DropdownMenuItem(value: value, child: Text(value))).toList(),
                    onChanged: (value) => sport.text = value ?? '',
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: region,
                    decoration: const InputDecoration(labelText: 'Аймаг / хот, дүүрэг'),
                    validator: (value) => (value ?? '').trim().length < 2
                        ? 'Байршлаа оруулна уу.'
                        : null,
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: preferredDate,
                    readOnly: true,
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: dialogContext,
                        initialDate: DateTime.now().add(const Duration(days: 1)),
                        firstDate: DateTime.now(),
                        lastDate: DateTime.now().add(const Duration(days: 365)),
                      );
                      if (picked != null) {
                        preferredDate.text = '${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
                      }
                    },
                    decoration: const InputDecoration(
                      labelText: 'Хүссэн өдөр (заавал биш)',
                      prefixIcon: Icon(Icons.calendar_month),
                      hintText: 'Дарж өдөр сонгоно уу',
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: phone,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: 'Холбоо барих утас'),
                    validator: (value) => (value ?? '').trim().length < 8
                        ? 'Утасны дугаараа зөв оруулна уу.'
                        : null,
                  ),
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('БОЛИХ'),
          ),
          FilledButton(
            onPressed: () {
              if (formKey.currentState!.validate()) {
                final dateText = preferredDate.text.trim();
                if (dateText.isNotEmpty && DateTime.tryParse(dateText) == null) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    const SnackBar(content: Text('Огноог YYYY-MM-DD хэлбэрээр оруулна уу.')),
                  );
                  return;
                }
                Navigator.pop(dialogContext, true);
              }
            },
            child: const Text('ХҮСЭЛТ ИЛГЭЭХ'),
          ),
        ],
      ),
    );

    if (submitted == true) {
      await _createRequest(
        provider: provider,
        title: title.text.trim(),
        details: [
          details.text.trim(),
          ...extraValues.entries.where((entry) => entry.value.text.trim().isNotEmpty)
              .map((entry) => '${entry.key}: ${entry.value.text.trim()}'),
        ].join(' | '),
        sport: sport.text.trim(),
        region: region.text.trim(),
        phone: phone.text.trim(),
        preferredDate: preferredDate.text.trim(),
      );
    }

    title.dispose();
    details.dispose();
    sport.dispose();
    region.dispose();
    phone.dispose();
    preferredDate.dispose();
    for (final controller in extraValues.values) { controller.dispose(); }
  }

  Future<void> _createRequest({
    required Map<String, dynamic> provider,
    required String title,
    required String details,
    required String sport,
    required String region,
    required String phone,
    required String preferredDate,
  }) async {
    final token = await _readToken();
    if (token == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final body = <String, dynamic>{
        'category': _category,
        'provider_user_id': provider['user_id'],
        'title': title,
        'details': details,
        'sport': sport.isEmpty ? null : sport,
        'region': region,
        'contact_phone': phone,
        'preferred_at': preferredDate.isEmpty
            ? null
            : DateTime.parse(preferredDate).toUtc().toIso8601String(),
      };

      await _api.postAuthorized('/services/requests', token: token, body: body);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Хүсэлт серверт амжилттай бүртгэгдлээ.')),
      );

      await _loadData();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _saving = false;
        });
      }
    }
  }

  Future<void> _showProviderForm() async {
    final formKey = GlobalKey<FormState>();
    final name = TextEditingController();
    final description = TextEditingController();
    final savedSport = _profile['sport']?.toString() ?? '';
    final sport = TextEditingController(text: _sportOptions.contains(savedSport) ? savedSport : '');
    final region = TextEditingController(text: _profile['region']?.toString() ?? '');
    final price = TextEditingController(text: '0');
    final credentials = TextEditingController();
    final extraValues = {for (final label in _providerFields) label: TextEditingController()};

    final submitted = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(widget.service.name + ' бүртгэл'),
        content: SizedBox(
          width: 420,
          child: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: name,
                    decoration: const InputDecoration(labelText: 'Нэр / байгууллагын нэр'),
                    validator: (value) => (value ?? '').trim().length < 2
                        ? 'Нэрээ оруулна уу.'
                        : null,
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: description,
                    minLines: 3,
                    maxLines: 5,
                    decoration: const InputDecoration(labelText: 'Үйлчилгээний танилцуулга'),
                    validator: (value) => (value ?? '').trim().length < 10
                        ? '10-аас дээш тэмдэгтээр тайлбарлана уу.'
                        : null,
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    value: _sportOptions.contains(sport.text) ? sport.text : null,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Спортын төрөл (сонгох)'),
                    items: _sportOptions.map((value) => DropdownMenuItem(value: value, child: Text(value))).toList(),
                    onChanged: (value) => sport.text = value ?? '',
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: region,
                    decoration: const InputDecoration(labelText: 'Аймаг / хот, дүүрэг'),
                    validator: (value) => (value ?? '').trim().length < 2
                        ? 'Байршлаа оруулна уу.'
                        : null,
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: price,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Эхлэх үнэ (₮)'),
                    validator: (value) {
                      final parsed = int.tryParse((value ?? '').trim());
                      if (parsed == null || parsed < 0) {
                        return 'Зөв үнэ оруулна уу.';
                      }
                      return null;
                    },
                  ),
                  ...extraValues.entries.map((entry) => Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: TextFormField(
                      controller: entry.value,
                      decoration: InputDecoration(labelText: entry.key),
                    ),
                  )),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: credentials,
                    decoration: const InputDecoration(
                      labelText: 'Мэргэжлийн эрх / үнэмлэх (заавал биш)',
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('БОЛИХ'),
          ),
          FilledButton(
            onPressed: () {
              if (formKey.currentState!.validate()) {
                Navigator.pop(dialogContext, true);
              }
            },
            child: const Text('БҮРТГҮҮЛЭХ'),
          ),
        ],
      ),
    );

    if (submitted == true) {
      await _saveProvider(
        name: name.text.trim(),
        description: [
          description.text.trim(),
          ...extraValues.entries.where((entry) => entry.value.text.trim().isNotEmpty)
              .map((entry) => '${entry.key}: ${entry.value.text.trim()}'),
        ].join(' | '),
        sport: sport.text.trim(),
        region: region.text.trim(),
        price: int.parse(price.text.trim()),
        credentials: credentials.text.trim(),
      );
    }

    name.dispose();
    description.dispose();
    sport.dispose();
    region.dispose();
    price.dispose();
    credentials.dispose();
    for (final controller in extraValues.values) { controller.dispose(); }
  }

  Future<void> _saveProvider({
    required String name,
    required String description,
    required String sport,
    required String region,
    required int price,
    required String credentials,
  }) async {
    final token = await _readToken();
    if (token == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      await _api.postAuthorized(
        '/services/providers/me',
        token: token,
        body: {
          'category': _category,
          'display_name': name,
          'description': description,
          'sport': sport.isEmpty ? null : sport,
          'region': region,
          'price_from': price,
          'credentials': credentials.isEmpty ? null : credentials,
        },
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Бүртгэл илгээгдлээ. Админ баталгаажуулсны дараа жагсаалтад харагдана.'),
        ),
      );

      await _loadData();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _saving = false;
        });
      }
    }
  }

  Future<void> _requestAction(
    int requestId,
    String action, {
    Map<String, dynamic> body = const {},
  }) async {
    final token = await _readToken();
    if (token == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      await _api.postAuthorized(
        '/services/requests/$requestId/$action',
        token: token,
        body: body,
      );
      await _loadData();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error.toString();
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _saving = false;
        });
      }
    }
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'pending':
        return 'Хүлээгдэж байна';
      case 'accepted':
        return 'Зөвшөөрсөн';
      case 'rejected':
        return 'Татгалзсан';
      case 'cancelled':
        return 'Цуцалсан';
      case 'completed':
        return 'Дууссан';
      default:
        return status;
    }
  }

  String _formatPrice(dynamic value) {
    final amount = value is num ? value.toInt() : int.tryParse('$value') ?? 0;
    if (amount == 0) return 'Үнийг тохиролцоно';
    final formatted = amount.toString().replaceAllMapped(
      RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
      (match) => '${match[1]},',
    );
    return 'Эхлэх үнэ: $formatted ₮';
  }

  Widget _buildProviderCard(Map<String, dynamic> provider) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: const Color(0xFFF0ECFF),
                  child: Icon(widget.service.icon, color: const Color(0xFF7043EA)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        provider['display_name']?.toString() ?? 'Үйлчилгээ үзүүлэгч',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        provider['region']?.toString() ?? '',
                        style: const TextStyle(color: Colors.blueGrey),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.verified, color: Colors.green),
              ],
            ),
            const SizedBox(height: 12),
            Text(provider['description']?.toString() ?? ''),
            if ((provider['sport'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Спорт: ${provider['sport']}'),
            ],
            if ((provider['credentials'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('Мэргэжлийн мэдээлэл: ${provider['credentials']}'),
            ],
            const SizedBox(height: 10),
            Text(
              _formatPrice(provider['price_from']),
              style: const TextStyle(fontWeight: FontWeight.w800, color: Color(0xFF3478FF)),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _saving ? null : () => _showRequestForm(provider),
                icon: const Icon(Icons.event_available),
                label: const Text('ҮЙЛЧИЛГЭЭ ХҮСЭХ'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRequestCard(Map<String, dynamic> request) {
    final id = request['id'] as int;
    final requesterId = request['requester_id'] as int?;
    final providerId = request['provider_user_id'] as int?;
    final status = request['status']?.toString() ?? 'pending';
    final isRequester = requesterId == _currentUserId;
    final isProvider = providerId == _currentUserId;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    request['title']?.toString() ?? 'Үйлчилгээний хүсэлт',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Chip(label: Text(_statusLabel(status))),
              ],
            ),
            const SizedBox(height: 6),
            Text(request['details']?.toString() ?? ''),
            const SizedBox(height: 6),
            Text('Байршил: ${request['region'] ?? '—'}'),
            Text('Холбоо барих: ${request['contact_phone'] ?? '—'}'),
            if ((request['response_note'] ?? '').toString().isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text('Хариу: ${request['response_note']}'),
              ),
            if (isProvider && status == 'pending') ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _saving
                          ? null
                          : () => _requestAction(
                                id,
                                'respond',
                                body: {'accepted': false, 'note': 'Хүсэлтийг хүлээн авах боломжгүй.'},
                              ),
                      child: const Text('ТАТГАЛЗАХ'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      onPressed: _saving
                          ? null
                          : () => _requestAction(
                                id,
                                'respond',
                                body: {'accepted': true, 'note': 'Хүсэлтийг хүлээн авлаа.'},
                              ),
                      child: const Text('ЗӨВШӨӨРӨХ'),
                    ),
                  ),
                ],
              ),
            ],
            if (isRequester && (status == 'pending' || status == 'accepted'))
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _saving ? null : () => _requestAction(id, 'cancel'),
                  child: const Text('ХҮСЭЛТ ЦУЦЛАХ'),
                ),
              ),
            if ((isRequester || isProvider) && status == 'accepted')
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _saving ? null : () => _requestAction(id, 'complete'),
                  child: const Text('ҮЙЛЧИЛГЭЭ ДУУССАН'),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchFilters() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _loadData(),
              decoration: InputDecoration(
                labelText: 'Нэр, үйлчилгээ, мэргэжлээр хайх',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  onPressed: () {
                    _searchController.clear();
                    _loadData();
                  },
                  icon: const Icon(Icons.close),
                ),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _regionController,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _loadData(),
              decoration: const InputDecoration(
                labelText: 'Аймаг / хот, дүүрэг',
                prefixIcon: Icon(Icons.location_on_outlined),
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _loading ? null : _loadData,
                icon: const Icon(Icons.filter_alt),
                label: const Text('ХАЙЛТ ХИЙХ'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.service.name),
        actions: [
          IconButton(
            tooltip: 'Шинэчлэх',
            onPressed: _loading ? null : _loadData,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF211052), Color(0xFF3157B8)],
                ),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(widget.service.icon, color: Colors.white, size: 34),
                  const SizedBox(height: 10),
                  Text(
                    widget.service.name,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 21,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _moduleWorkflow,
                    style: const TextStyle(color: Colors.white70),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _buildSearchFilters(),
            const SizedBox(height: 14),
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'БАТАЛГААЖСАН ҮЙЛЧИЛГЭЭ',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15),
                  ),
                ),
                Text('${_providers.length}'),
              ],
            ),
            const SizedBox(height: 10),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null) ...[
              Card(
                color: const Color(0xFFF3ECFF),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(
                    _error!,
                    style: const TextStyle(color: Color(0xFF6338D8)),
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
            if (!_loading && _providers.isEmpty && _error == null)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Column(
                    children: [
                      Icon(Icons.search_off, size: 36, color: Colors.blueGrey),
                      SizedBox(height: 8),
                      Text(
                        'Одоогоор баталгаажсан үйлчилгээ үзүүлэгч алга.',
                        textAlign: TextAlign.center,
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Хайлтын нөхцөлөө өөрчлөх эсвэл үйлчилгээ үзүүлэгчээр бүртгүүлж болно.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.blueGrey, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            ..._providers.map(_buildProviderCard),
            const SizedBox(height: 6),
            OutlinedButton.icon(
              onPressed: _saving ? null : _showProviderForm,
              icon: const Icon(Icons.person_add_alt_1),
              label: const Text('ҮЙЛЧИЛГЭЭ ҮЗҮҮЛЭГЧЭЭР БҮРТГҮҮЛЭХ'),
            ),
            const SizedBox(height: 22),
            const Text(
              'МИНИЙ ХҮСЭЛТҮҮД',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15),
            ),
            const SizedBox(height: 10),
            if (_requests.where((item) => item['category'] == _category).isEmpty && !_loading)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Одоогоор энэ цэстэй холбоотой хүсэлт алга.'),
                ),
              ),
            ..._requests
                .where((item) => item['category'] == _category)
                .map(_buildRequestCard),
            const SizedBox(height: 20),
            const Text(
              'Тайлбар: Үйлчилгээ үзүүлэгчийн профайл админы баталгаажуулалтын дараа нийтэд харагдана. Захиалга, хүсэлтийн төлөв серверт хадгалагдана.',
              style: TextStyle(fontSize: 12, color: Colors.blueGrey),
            ),
          ],
        ),
      ),
    );
  }
}
