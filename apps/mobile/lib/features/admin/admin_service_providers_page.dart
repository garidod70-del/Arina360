import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../core/network/api_client.dart';

class AdminServiceProvidersPage extends StatefulWidget {
  const AdminServiceProvidersPage({super.key});

  @override
  State<AdminServiceProvidersPage> createState() => _AdminServiceProvidersPageState();
}

class _AdminServiceProvidersPageState extends State<AdminServiceProvidersPage> {
  static const _storage = FlutterSecureStorage();
  final ApiClient _api = ApiClient();
  List<Map<String, dynamic>> _providers = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPending();
  }

  @override
  void dispose() {
    _api.close();
    super.dispose();
  }

  Future<void> _loadPending() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await _storage.read(key: 'arena_access_token');
      if (token == null || token.isEmpty) {
        throw const ApiException(401, 'Нэвтрэх эрх олдсонгүй.');
      }
      final providers = await _api.getList(
        '/services/providers/pending?verification_status=pending',
        token: token,
      );
      if (!mounted) return;
      setState(() => _providers = providers);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _categoryLabel(String category) {
    const names = {
      'coach': 'Дасгалжуулагч',
      'sports_doctor': 'Спортын эмч',
      'strength_specialist': 'Хүчний мэргэжилтэн',
      'sports_psychologist': 'Сэтгэл зүйч',
      'sports_nutritionist': 'Хоол зүйч',
      'physiotherapist': 'Хөдөлгөөн засалч',
      'sports_analyst': 'Спортын шинжээч',
      'venue_booking': 'Заал захиалга',
      'sports_store': 'Спорт бараа худалдаа',
      'clubs_training': 'Сургалт, клубууд',
    };
    return names[category] ?? category;
  }

  Future<void> _reviewProvider(
    Map<String, dynamic> provider, {
    required bool approved,
  }) async {
    final noteController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(approved ? 'Үйлчилгээ баталгаажуулах' : 'Бүртгэлээс татгалзах'),
        content: TextField(
          controller: noteController,
          minLines: 2,
          maxLines: 4,
          decoration: const InputDecoration(
            labelText: 'Шалгалтын тэмдэглэл',
            hintText: 'Баримт, мэргэжлийн эрхийн шалгалтын тайлбар',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('БОЛИХ'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('ШИЙДВЭР БҮРТГЭХ'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final token = await _storage.read(key: 'arena_access_token');
      if (token == null) {
        noteController.dispose();
        return;
      }

      setState(() {
        _loading = true;
        _error = null;
      });

      try {
        await _api.postAuthorized(
          '/services/providers/${provider['id']}/verify',
          token: token,
          body: {
            'approved': approved,
            'note': noteController.text.trim(),
          },
        );
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                approved
                    ? 'Үйлчилгээ үзүүлэгчийг баталгаажууллаа.'
                    : 'Үйлчилгээ үзүүлэгчийн бүртгэлээс татгалзлаа.',
              ),
            ),
          );
        }
        await _loadPending();
      } catch (error) {
        if (mounted) setState(() => _error = error.toString());
      } finally {
        if (mounted) setState(() => _loading = false);
      }
    }

    noteController.dispose();
  }

  Widget _providerCard(Map<String, dynamic> provider) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              provider['display_name']?.toString() ?? 'Үйлчилгээ үзүүлэгч',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
            ),
            const SizedBox(height: 5),
            Text(_categoryLabel(provider['category']?.toString() ?? '')),
            const SizedBox(height: 8),
            Text(provider['description']?.toString() ?? ''),
            const SizedBox(height: 8),
            Text('Байршил: ${provider['region'] ?? '—'}'),
            Text('Спорт: ${provider['sport'] ?? '—'}'),
            Text('Үнэ: ${provider['price_from'] ?? 0} ₮'),
            Text('Мэргэжлийн эрх: ${provider['credentials'] ?? 'Мэдээлэл оруулаагүй'}'),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _loading
                        ? null
                        : () => _reviewProvider(provider, approved: false),
                    child: const Text('ТАТГАЛЗАХ'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _loading
                        ? null
                        : () => _reviewProvider(provider, approved: true),
                    icon: const Icon(Icons.verified_user),
                    label: const Text('БАТАЛГААЖУУЛАХ'),
                  ),
                ),
              ],
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
        title: const Text('Админ • Үйлчилгээний бүртгэл'),
        actions: [
          IconButton(
            onPressed: _loading ? null : _loadPending,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadPending,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text(
              'БАТАЛГААЖУУЛАХ ХҮСЭЛТҮҮД',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
            ),
            const SizedBox(height: 8),
            const Text(
              'Мэргэжлийн үнэмлэх, байгууллагын мэдээлэл болон үйлчилгээний танилцуулгыг шалгасны дараа шийдвэр гаргана уу.',
              style: TextStyle(color: Colors.blueGrey),
            ),
            const SizedBox(height: 14),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null)
              Card(
                color: const Color(0xFFFFF3E8),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Text(_error!),
                ),
              ),
            if (!_loading && _providers.isEmpty && _error == null)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Text(
                    'Одоогоор баталгаажуулах хүсэлт алга.',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ..._providers.map(_providerCard),
          ],
        ),
      ),
    );
  }
}
