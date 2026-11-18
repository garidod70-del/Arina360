import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../network/api_client.dart';

class QPayPaymentDialog {
  static Future<void> open({
    required BuildContext context,
    required ApiClient api,
    required String token,
    required String orderType,
    required int orderId,
    required VoidCallback onPaid,
  }) async {
    final invoice = await api.postAuthorized(
      '/payments/qpay/invoice',
      token: token,
      body: {'order_type': orderType, 'order_id': orderId},
    );
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialog) => AlertDialog(
          title: const Text('QPay төлбөр'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('Нэхэмжлэл #${invoice['id']} • ${invoice['amount']} ₮'),
              const SizedBox(height: 12),
              if ((invoice['qr_text'] ?? '').toString().isNotEmpty)
                QrImageView(data: invoice['qr_text'].toString(), size: 220),
              if ((invoice['short_url'] ?? '').toString().isNotEmpty)
                SelectableText(invoice['short_url'].toString()),
              const SizedBox(height: 8),
              const Text('Банкны апп-аараа QR кодыг уншуулж төлнө үү.'),
            ]),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('ДАРАА ТӨЛӨХ'),
            ),
            FilledButton(
              onPressed: () async {
                try {
                  final checked = await api.postAuthorized(
                    '/payments/qpay/invoices/${invoice['id']}/check',
                    token: token,
                    body: const {},
                  );
                  if (checked['status'] == 'paid') {
                    if (dialogContext.mounted) Navigator.pop(dialogContext);
                    onPaid();
                  } else {
                    ScaffoldMessenger.of(dialogContext).showSnackBar(
                      const SnackBar(content: Text('Төлбөр хараахан баталгаажаагүй байна.')),
                    );
                  }
                } catch (error) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    SnackBar(content: Text(error.toString())),
                  );
                }
              },
              child: const Text('ТӨЛБӨР ШАЛГАХ'),
            ),
          ],
        ),
      ),
    );
  }
}
