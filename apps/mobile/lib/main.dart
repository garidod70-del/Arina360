import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:open_filex/open_filex.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

void main() => runApp(const Arena360App());

const navy = Color(0xFF101B36);
const blue = Color(0xFF2878FF);
const pageBg = Color(0xFFF4F7FC);

class ServiceItem {
  final IconData icon;
  final String name;
  final String description;
  const ServiceItem(this.icon, this.name, this.description);
}

const services = <ServiceItem>[
  ServiceItem(Icons.sports, 'Шүүгч', 'Спортын төрлөөр шүүгч хайх'),
  ServiceItem(Icons.groups, 'Клуб, сургалтууд', 'Клуб, секц болон сургалт'),
  ServiceItem(Icons.emoji_events, 'Спортын тэмцээн', 'Багийн, ганцаарчилсан, үндэсний спорт'),
  ServiceItem(Icons.stadium, 'Заал түрээс', 'Заал, талбайн цаг захиалга'),
  ServiceItem(Icons.shopping_bag, 'Спорт бараа', 'Спортын хувцас, хэрэгсэл'),
  ServiceItem(Icons.school, 'Дасгалжуулагч, шүүгчийн сургалт', 'Сургалт, шалгалт, гэрчилгээ'),
  ServiceItem(Icons.fitness_center, 'Фитнесс', 'Фитнесс төв, эрх, дасгалжуулагч'),
];

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
  final _repeatPassword = TextEditingController();
  bool _isRegister = false;
  bool _showPassword = false;
  bool _acceptedTerms = false;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    _repeatPassword.dispose();
    super.dispose();
  }

  String? _validatePhone(String? value) {
    return (value ?? '').trim().isNotEmpty
        ? null
        : 'Утасны дугаар оруулна уу';
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    if (_isRegister && !_acceptedTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Үйлчилгээний нөхцөлийг зөвшөөрнө үү')),
      );
      return;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => HomePage(phone: _phone.text.trim()),
      ),
    );
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
                      maxLength: 8,
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
                    if (_isRegister) ...[
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _repeatPassword,
                        obscureText: !_showPassword,
                        decoration: const InputDecoration(
                          labelText: 'Нууц үг давтах',
                          prefixIcon: Icon(Icons.lock_reset),
                        ),
                        validator: (value) {
                          if ((value ?? '').isEmpty) return 'Нууц үгээ давтана уу';
                          if (value != _password.text) return 'Нууц үг таарахгүй байна';
                          return null;
                        },
                      ),
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        value: _acceptedTerms,
                        onChanged: (value) =>
                            setState(() => _acceptedTerms = value ?? false),
                        controlAffinity: ListTileControlAffinity.leading,
                        title: const Text(
                          'Үйлчилгээний нөхцөлийг зөвшөөрөх',
                          style: TextStyle(fontSize: 13),
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    SizedBox(
                      height: 52,
                      child: FilledButton(
                        style: FilledButton.styleFrom(backgroundColor: blue),
                        onPressed: _submit,
                        child: Text(_isRegister ? 'БҮРТГҮҮЛЭХ' : 'НЭВТРЭХ'),
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
                    const Text(
                      'Туршилтын нэвтрэлт: дурын утасны дугаар болон хоосон биш нууц үгээр нэвтэрнэ. Серверийн баталгаажуулалт холбогдоогүй.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 11, color: Colors.blueGrey),
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

class HomePage extends StatelessWidget {
  final String phone;
  const HomePage({super.key, required this.phone});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ARENA 360'),
        actions: [
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
                  'Тавтай морил, $phone',
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


const refereeSports=<String,List<String>>{'Багийн спорт':['Сагсан бөмбөг','Волейбол','3x3','Хөлбөмбөг'],'Ганцаарчилсан спорт':['Жүдо','Чөлөөт бөх'],'Үндэсний спорт':['Үндэсний бөх','Шагайн харваа']};
const refereeRanks=<String,List<String>>{'Багийн спорт':['Олон улсын','Улсын','I зэрэг','II зэрэг','III зэрэг'],'Ганцаарчилсан спорт':['Олон улсын','Улсын','I зэрэг','II зэрэг','III зэрэг'],'Үндэсний бөх':['Хөлийн цэц','Засуул','Гарын даа'],'Шагайн харваа':['Цол зэрэгтэй шүүгч','Улсын цолтой','Аймгийн цолтой','Зэрэгтэй']};
class RefereeBookingPage extends StatefulWidget{const RefereeBookingPage({super.key});@override State<RefereeBookingPage> createState()=>_RefereeBookingPageState();}
class _RefereeBookingPageState extends State<RefereeBookingPage>{
String role='Тэмцээн зохион байгуулагч',category='Багийн спорт',sport='Сагсан бөмбөг',rank='Улсын',booking='Нэг шүүгч',payment='Нэг тоглолтоор';
final count=TextEditingController(text:'1'),rate=TextEditingController(text:'50000'),days=TextEditingController(text:'1'),transport=TextEditingController(text:'0'),food=TextEditingController(text:'0');
bool addTransport=false,addFood=false,prepared=false;
@override void dispose(){count.dispose();rate.dispose();days.dispose();transport.dispose();food.dispose();super.dispose();}
List<String> get ranks=>category=='Үндэсний спорт'?(sport=='Үндэсний бөх'?refereeRanks['Үндэсний бөх']!:refereeRanks['Шагайн харваа']!):refereeRanks[category]!;
int n(TextEditingController c)=>int.tryParse(c.text)??0;
int get base=>n(count).clamp(0,10000)*n(rate).clamp(0,100000000)*(payment=='Нэг өдрөөр'?n(days).clamp(1,365):1);
int get total=>base+(addTransport?n(transport).clamp(0,100000000):0)+(addFood?n(food).clamp(0,100000000):0);
Widget sec(String t,Widget w)=>Padding(padding:const EdgeInsets.only(bottom:15),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(t,style:const TextStyle(fontWeight:FontWeight.w800,color:navy,fontSize:15)),const SizedBox(height:8),w]));
Widget dd(String label,String value,List<String> values,ValueChanged<String?> change)=>DropdownButtonFormField<String>(value:value,isExpanded:true,decoration:InputDecoration(labelText:label),items:values.map((v)=>DropdownMenuItem(value:v,child:Text(v))).toList(),onChanged:change);
Widget fld(String label,TextEditingController c)=>TextField(controller:c,keyboardType:TextInputType.number,onChanged:(_)=>setState((){}),decoration:InputDecoration(labelText:label));
@override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('Шүүгч захиалга')),body:ListView(padding:const EdgeInsets.all(18),children:[
Container(padding:const EdgeInsets.all(18),decoration:BoxDecoration(gradient:const LinearGradient(colors:[navy,Color(0xFF244B91)]),borderRadius:BorderRadius.circular(18)),child:const Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('REFEREE SERVICE',style:TextStyle(color:Colors.white70,fontWeight:FontWeight.bold)),SizedBox(height:7),Text('Мэргэжлийн шүүгчийн захиалга',style:TextStyle(color:Colors.white,fontSize:21,fontWeight:FontWeight.w900)),SizedBox(height:5),Text('Шүүгчийн төрөл, зэрэглэл, баг болон зардлаа тооцоол.',style:TextStyle(color:Colors.white70))])),
const SizedBox(height:18),
sec('1. Хэрэглэгчийн төрөл',SegmentedButton<String>(segments:const[ButtonSegment(value:'Тэмцээн зохион байгуулагч',label:Text('Зохион байгуулагч')),ButtonSegment(value:'Шүүгч',label:Text('Шүүгч'))],selected:{role},onSelectionChanged:(v)=>setState(()=>role=v.first))),
sec('2. Спортын ангилал',dd('Ангилал',category,refereeSports.keys.toList(),(v)=>setState(()=>{category=v!,sport=refereeSports[category]!.first,rank=ranks.first}))),
sec('Спортын төрөл',dd('Спорт',sport,refereeSports[category]!, (v)=>setState(()=>{sport=v!,rank=ranks.first}))),
sec('3. Шүүгчийн зэрэглэл / үүрэг',dd('Зэрэглэл',rank,ranks,(v)=>setState(()=>rank=v!))),
sec('4. Захиалгын төрөл',dd('Захиалга',booking,const['Нэг шүүгч','Шүүгчдийн баг (Crew)','Спартакиад / спортын наадмын багц'],(v)=>setState(()=>booking=v!))),
sec('5. Төлбөрийн тооцоолол',Column(children:[
dd('Тооцох хэлбэр',payment,const['Нэг тоглолтоор','Нэг өдрөөр','Нэг даваагаар'],(v)=>setState(()=>payment=v!)),
const SizedBox(height:9),Row(children:[Expanded(child:fld('Шүүгчийн тоо',count)),const SizedBox(width:10),Expanded(child:fld('Нэгж үнэ (₮)',rate))]),
if(payment=='Нэг өдрөөр')... [const SizedBox(height:9),fld('Ажиллах өдөр',days)],
SwitchListTile(contentPadding:EdgeInsets.zero,title:const Text('Унааны зардал нэмэх'),value:addTransport,onChanged:(v)=>setState(()=>addTransport=v)),
if(addTransport)fld('Нийт унааны зардал (₮)',transport),
SwitchListTile(contentPadding:EdgeInsets.zero,title:const Text('Хоолны зардал нэмэх'),value:addFood,onChanged:(v)=>setState(()=>addFood=v)),
if(addFood)fld('Нийт хоолны зардал (₮)',food),
])),
Container(padding:const EdgeInsets.all(18),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xFFDCE5F2))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
const Text('ТООЦООНЫ НЭГТГЭЛ',style:TextStyle(color:navy,fontWeight:FontWeight.w900)),const SizedBox(height:10),
Text('Үндсэн төлбөр: '+base.toString()+' ₮'),if(addTransport)Text('Унаа: '+n(transport).toString()+' ₮'),if(addFood)Text('Хоол: '+n(food).toString()+' ₮'),
const Divider(height:22),Text('НИЙТ ДҮН: '+total.toString()+' ₮',style:const TextStyle(fontWeight:FontWeight.w900,color:blue,fontSize:20)),
const Text('Жишиг тооцоо. Бодит тарифыг админ болон үйлчилгээ үзүүлэгч баталгаажуулна.',style:TextStyle(fontSize:11,color:Colors.blueGrey)),
])),
const SizedBox(height:15),FilledButton.icon(style:FilledButton.styleFrom(backgroundColor:blue,padding:const EdgeInsets.symmetric(vertical:15)),onPressed:()=>setState(()=>prepared=true),icon:const Icon(Icons.send),label:Text(role=='Шүүгч'?'ШҮҮГЧИЙН ПРОФАЙЛ БЭЛТГЭХ':'ЗАХИАЛГЫН МЭДЭЭЛЭЛ БЭЛТГЭХ')),
if(prepared)const Text('Мэдээлэл бэлэн. Онлайн захиалга, төлбөрийн баталгаажуулалт серверийн холболт шаардлагатай.',textAlign:TextAlign.center,style:TextStyle(color:Colors.blueGrey,fontSize:12)),
const SizedBox(height:24),
]));}
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
