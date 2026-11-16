import 'package:flutter/material.dart';
void main()=>runApp(const ArenaApp());
const navy=Color(0xFF101B36), blue=Color(0xFF2878FF);
const services=<({IconData icon,String name,String detail})>[
(icon:Icons.sports,name:'Шүүгч',detail:'Спортын төрлөөр шүүгч хайх'),
(icon:Icons.groups,name:'Клуб, сургалтууд',detail:'Клуб, секц болон сургалт'),
(icon:Icons.emoji_events,name:'Спортын тэмцээн',detail:'Багийн, ганцаарчилсан, үндэсний спорт'),
(icon:Icons.stadium,name:'Заал түрээс',detail:'Заал, талбайн цаг захиалга'),
(icon:Icons.shopping_bag,name:'Спорт бараа',detail:'Спортын хувцас, хэрэгсэл'),
(icon:Icons.school,name:'Дасгалжуулагч, шүүгчийн сургалт',detail:'Сургалт, шалгалт, гэрчилгээ'),
(icon:Icons.fitness_center,name:'Фитнесс',detail:'Фитнесс төв, эрх, дасгалжуулагч'),
];
class ArenaApp extends StatelessWidget{const ArenaApp({super.key});@override Widget build(BuildContext c)=>MaterialApp(title:'ARENA 360',debugShowCheckedModeBanner:false,theme:ThemeData(useMaterial3:true,colorScheme:ColorScheme.fromSeed(seedColor:blue),scaffoldBackgroundColor:const Color(0xFFF4F7FC),appBarTheme:const AppBarTheme(backgroundColor:navy,foregroundColor:Colors.white)),home:const AuthPage());}
class AuthPage extends StatefulWidget{const AuthPage({super.key});@override State<AuthPage> createState()=>_AuthPageState();}
class _AuthPageState extends State<AuthPage>{
 final form=GlobalKey<FormState>();final phone=TextEditingController(),pass=TextEditingController(),repeat=TextEditingController();bool register=true,showPass=false,accepted=false;
 @override void dispose(){phone.dispose();pass.dispose();repeat.dispose();super.dispose();}
 String? phoneCheck(String? v)=>RegExp(r'^\\d{8}$').hasMatch((v??'').trim())?null:'8 оронтой утасны дугаар оруулна уу';
 void submit(){if(!form.currentState!.validate())return;if(register&&!accepted){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('Үйлчилгээний нөхцөлийг зөвшөөрнө үү')));return;}Navigator.pushReplacement(context,MaterialPageRoute(builder:(_)=>HomePage(phone:phone.text)));}
 @override Widget build(BuildContext c)=>Scaffold(body:SafeArea(child:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(24),child:ConstrainedBox(constraints:const BoxConstraints(maxWidth:440),child:Form(key:form,child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
 Container(height:76,width:76,alignment:Alignment.center,decoration:BoxDecoration(color:navy,borderRadius:BorderRadius.circular(22)),child:const Icon(Icons.sports_martial_arts,color:Colors.white,size:42)),
 const SizedBox(height:20),const Text('ARENA 360',style:TextStyle(fontSize:30,fontWeight:FontWeight.w900,color:navy,letterSpacing:1.4)),const Text('ONE PLATFORM. ALL SPORTS.',style:TextStyle(color:blue,fontWeight:FontWeight.bold)),
 const SizedBox(height:32),Text(register?'Шинэ хэрэглэгч бүртгүүлэх':'Нэвтрэх',style:const TextStyle(fontSize:23,fontWeight:FontWeight.bold,color:navy)),const SizedBox(height:20),
 TextFormField(controller:phone,keyboardType:TextInputType.phone,maxLength:8,decoration:const InputDecoration(labelText:'Утасны дугаар',prefixIcon:Icon(Icons.phone),counterText:''),validator:phoneCheck),
 const SizedBox(height:12),TextFormField(controller:pass,obscureText:!showPass,decoration:InputDecoration(labelText:'Нууц үг',prefixIcon:const Icon(Icons.lock_outline),suffixIcon:IconButton(onPressed:()=>setState(()=>showPass=!showPass),icon:Icon(showPass?Icons.visibility_off:Icons.visibility))),validator:(v)=>(v==null||v.length<8)?'Нууц үг 8-аас доошгүй тэмдэгт байна':null),
 if(register)...[const SizedBox(height:12),TextFormField(controller:repeat,obscureText:!showPass,decoration:const InputDecoration(labelText:'Нууц үг давтах',prefixIcon:Icon(Icons.lock_reset)),validator:(v)=>(v??'').isEmpty?'Нууц үгээ давтана уу':v!=pass.text?'Нууц үг таарахгүй байна':null),CheckboxListTile(contentPadding:EdgeInsets.zero,value:accepted,onChanged:(v)=>setState(()=>accepted=v??false),controlAffinity:ListTileControlAffinity.leading,title:const Text('Үйлчилгээний нөхцөлийг зөвшөөрөх',style:TextStyle(fontSize:13)))],
 const SizedBox(height:16),SizedBox(height:52,child:FilledButton(style:FilledButton.styleFrom(backgroundColor:blue),onPressed:submit,child:Text(register?'БҮРТГҮҮЛЭХ':'НЭВТРЭХ'))),
 TextButton(onPressed:()=>setState(()=>register=!register),child:Text(register?'Бүртгэлтэй юу? Нэвтрэх':'Шинэ хэрэглэгч үү? Бүртгүүлэх')),
 const Text('Туршилтын эхний хувилбар: бодит OTP болон серверийн бүртгэл хараахан холбогдоогүй.',textAlign:TextAlign.center,style:TextStyle(fontSize:11,color:Colors.blueGrey))
 ]))))));
}}
class HomePage extends StatelessWidget{final String phone;const HomePage({super.key,required this.phone});@override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('ARENA 360'),actions:[IconButton(onPressed:()=>Navigator.pushAndRemoveUntil(c,MaterialPageRoute(builder:(_)=>const AuthPage()),(_)=>false),icon:const Icon(Icons.logout))]),body:ListView(padding:const EdgeInsets.all(18),children:[
 Container(padding:const EdgeInsets.all(22),decoration:BoxDecoration(gradient:const LinearGradient(colors:[navy,Color(0xFF244B91)]),borderRadius:BorderRadius.circular(20)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('ONE PLATFORM. ALL SPORTS.',style:TextStyle(color:Colors.white,fontSize:24,fontWeight:FontWeight.w900)),const SizedBox(height:10),Text('Тавтай морил, $phone',style:const TextStyle(color:Colors.white70))]),
 const SizedBox(height:22),const Text('ҮЙЛЧИЛГЭЭНҮҮД',style:TextStyle(fontSize:17,fontWeight:FontWeight.w900,color:navy)),const SizedBox(height:12),
 GridView.builder(shrinkWrap:true,physics:const NeverScrollableScrollPhysics(),itemCount:services.length,gridDelegate:const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount:2,crossAxisSpacing:12,mainAxisSpacing:12,childAspectRatio:1.05),itemBuilder:(c,i){final s=services[i];return InkWell(borderRadius:BorderRadius.circular(16),onTap:()=>Navigator.push(c,MaterialPageRoute(builder:(_)=>ServicePage(service:s))),child:Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(16),border:Border.all(color:const Color(0xFFE5EAF2))),child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.spaceBetween,children:[Icon(s.icon,color:blue,size:30),Text(s.name,style:const TextStyle(fontWeight:FontWeight.bold,color:navy)),const Icon(Icons.arrow_forward,color:blue,size:18)])));})
 ]));}}
class ServicePage extends StatelessWidget{final ({IconData icon,String name,String detail}) service;const ServicePage({super.key,required this.service});@override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:Text(service.name)),body:Center(child:Padding(padding:const EdgeInsets.all(28),child:Column(mainAxisSize:MainAxisSize.min,children:[Icon(service.icon,color:blue,size:64),const SizedBox(height:18),Text(service.name,style:const TextStyle(fontSize:22,fontWeight:FontWeight.bold,color:navy),textAlign:TextAlign.center),const SizedBox(height:10),Text(service.detail,textAlign:TextAlign.center),const SizedBox(height:20),const Text('Дэлгэрэнгүй үйлчилгээний модуль дараагийн хөгжүүлэлтийн шатанд нэмэгдэнэ.',textAlign:TextAlign.center,style:TextStyle(color:Colors.blueGrey,fontSize:12))]))));}}
