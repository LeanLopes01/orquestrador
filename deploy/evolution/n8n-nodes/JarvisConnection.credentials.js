class JarvisConnection {
 constructor(){
  this.name='jarvisConnection';this.displayName='Jarvis · Conta protegida';
  this.documentationUrl='https://docs.n8n.io/integrations/creating-nodes/build/reference/credentials-files/';
  this.properties=[
   {displayName:'Chave do estado local',name:'stateSecret',type:'string',typeOptions:{password:true},default:'',required:true,description:'Gerada pelo instalador. Preservar ao editar a conta; protege cache de tokens e dados do conector.'},
   {displayName:'Configuração da conta (JSON)',name:'configuration',type:'string',typeOptions:{password:true},default:'{}',required:true,description:'Campos do manifesto desta integração. Armazenados criptografados pelo n8n. Nunca incluir no workflow ou em prompts.'},
   {displayName:'Origens adicionais permitidas',name:'origins',type:'string',default:'',description:'Lista separada por vírgulas, cadastrada pelo administrador, para instâncias próprias. Ex.: https://cloud.example.com'},
   {displayName:'Permitir rede privada nessas origens',name:'privateNetwork',type:'boolean',default:false,description:'Somente para instâncias próprias explicitamente cadastradas; não libera URLs arbitrárias.'}
  ];
 }
}
module.exports={JarvisConnection};
