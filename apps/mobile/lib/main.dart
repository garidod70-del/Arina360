import 'package:flutter/material.dart';

void main() => runApp(const Arena360App());

class Arena360App extends StatelessWidget {
  const Arena360App({super.key});
  @override
  Widget build(BuildContext context) {
    const navy = Color(0xFF101B36);
    const blue = Color(0xFF2878FF);
    return MaterialApp(
      title: 'ARENA 360',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(useMaterial3: true, colorScheme: ColorScheme.fromSeed(seedColor: blue), scaffoldBackgroundColor: const Color(0xFFF5F7FB), appBarTheme: const AppBarTheme(backgroundColor: navy, foregroundColor: Colors.white)),
      home: const WelcomePage(),
    );
  }
}

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});
  static const services = <(IconData, String)>[
    (Icons.sports, 'Шүүгч'),
    (Icons.groups, 'Клуб, сургалт'),
    (Icons.emoji_events, 'Спортын тэмцээн'),
    (Icons.stadium, 'Заал түрээс'),
    (Icons.shopping_bag, 'Спорт бараа'),
    (Icons.school, 'Дасгалжуулагч, шүүгчийн сургалт'),
    (Icons.fitness_center, 'Фитнесс'),
  ];
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('ARENA 360', style: TextStyle(fontWeight: FontWeight.w800)), actions: [IconButton(onPressed: () {}, icon: const Icon(Icons.notifications_none))]),
    body: SafeArea(child: ListView(padding: const EdgeInsets.all(18), children: [
      Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(borderRadius: BorderRadius.circular(22), gradient: const LinearGradient(colors: [Color(0xFF101B36), Color(0xFF245EDB)], begin: Alignment.topLeft, end: Alignment.bottomRight)), child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('СПОРТЫН ҮЙЛЧИЛГЭЭ НЭГ ДОР', style: TextStyle(color: Colors.white70, fontSize: 12, letterSpacing: 1.2)),
        SizedBox(height: 10), Text('Спортын ертөнц таны гарт.', style: TextStyle(color: Colors.white, fontSize: 27, height: 1.15, fontWeight: FontWeight.w800)),
        SizedBox(height: 14), Text('Шүүгч, клуб, тэмцээн, заал, бараа, сургалт, фитнесс', style: TextStyle(color: Colors.white70, fontSize: 13)),
      ])),
      const SizedBox(height: 24), const Text('ҮЙЛЧИЛГЭЭНҮҮД', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14, letterSpacing: 1)), const SizedBox(height: 12),
      GridView.builder(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), itemCount: services.length, gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12, childAspectRatio: 1.28), itemBuilder: (context, index) {
        final item = services[index];
        return Material(color: Colors.white, borderRadius: BorderRadius.circular(18), child: InkWell(borderRadius: BorderRadius.circular(18), onTap: () => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${item.$2} — хөгжүүлэлтийн дараагийн шатанд идэвхжинэ'))), child: Padding(padding: const EdgeInsets.all(15), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [Icon(item.$1, color: const Color(0xFF2878FF), size: 30), const SizedBox(height: 12), Text(item.$2, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14))]))));
      }),
      const SizedBox(height: 18), const Text('Эхний хувилбарын интерфэйс. Бүртгэл, захиалга, төлбөр болон серверийн холболтыг дараагийн хөгжүүлэлтийн шатанд холбоно.', style: TextStyle(color: Color(0xFF657089), fontSize: 12, height: 1.5)),
    ])),
  );
}
