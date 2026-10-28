const fs = require('fs');
const sharp = require('sharp');

const T = [
 ['role','VAI TRÒ',60,60,280,['PK  Mã vai trò','Tên vai trò','Mô tả']],
 ['account','TÀI KHOẢN',390,60,330,['PK  Mã tài khoản','FK  Mã vai trò','Họ tên','Email','Số điện thoại','Mật khẩu mã hóa','Trạng thái']],
 ['customer','KHÁCH HÀNG',780,60,320,['PK  Mã khách hàng','FK  Mã tài khoản','Loại khách hàng','Thông tin liên hệ','Trạng thái']],
 ['audit','NHẬT KÝ THAO TÁC',60,390,300,['PK  Mã nhật ký','FK  Mã tài khoản','Hành động','Đối tượng tác động','Thời gian','Chi tiết']],
 ['setting','CẤU HÌNH HỆ THỐNG',390,390,330,['PK  Mã cấu hình','FK  Người cập nhật','Tên tham số','Giá trị','Thời gian cập nhật']],

 ['chat','PHIÊN TRÒ CHUYỆN',1220,60,340,['PK  Mã phiên','FK  Mã khách hàng','FK  Nhân viên tiếp nhận','Thời gian bắt đầu','Thời gian kết thúc','Kênh trò chuyện','Trạng thái']],
 ['message','TIN NHẮN',1630,60,330,['PK  Mã tin nhắn','FK  Mã phiên','FK  Người gửi','Nội dung','Loại người gửi','Thời gian']],
 ['sentiment','PHÂN TÍCH CẢM XÚC',2030,60,330,['PK  Mã phân tích','FK  Mã tin nhắn','Nhãn cảm xúc','Điểm cảm xúc','Thời gian']],
 ['suggestion','GỢI Ý TRẢ LỜI AI',2030,350,330,['PK  Mã gợi ý','FK  Mã tin nhắn','Nội dung nháp','Độ tin cậy','Trạng thái duyệt','Thời gian']],
 ['handover','CHUYỂN GIAO',1220,390,340,['PK  Mã chuyển giao','FK  Mã phiên','FK  Nhân viên tiếp nhận','Lý do','Trạng thái','Thời gian yêu cầu','Thời gian tiếp nhận']],
 ['summary','TÓM TẮT HỖ TRỢ',1630,390,330,['PK  Mã tóm tắt','FK  Mã phiên','FK  Mã yêu cầu','Nội dung tóm tắt','Mô hình AI','Thời gian tạo']],

 ['category','DANH MỤC YÊU CẦU',60,820,300,['PK  Mã danh mục','Tên danh mục','Mô tả']],
 ['ticket','YÊU CẦU HỖ TRỢ',420,760,390,['PK  Mã yêu cầu','FK  Mã khách hàng','FK  Mã phiên','FK  Mã danh mục','Tiêu đề','Nội dung','Mức ưu tiên','Trạng thái','Ngày tạo, ngày đóng']],
 ['assignment','LỊCH SỬ PHÂN CÔNG',880,760,360,['PK  Mã phân công','FK  Mã yêu cầu','FK  Nhân viên được giao','FK  Người phân công','Thời gian']],
 ['status','LỊCH SỬ TRẠNG THÁI',60,1160,340,['PK  Mã lịch sử','FK  Mã yêu cầu','FK  Người cập nhật','Trạng thái cũ','Trạng thái mới','Ghi chú','Thời gian']],
 ['reply','PHẢN HỒI YÊU CẦU',460,1160,350,['PK  Mã phản hồi','FK  Mã yêu cầu','FK  Người gửi','Nội dung','Thời gian']],
 ['attachment','TỆP ĐÍNH KÈM',880,1160,330,['PK  Mã tệp','FK  Mã yêu cầu','FK  Người tải lên','Tên tệp','Đường dẫn','Loại tệp','Thời gian']],
 ['evaluation','ĐÁNH GIÁ HỖ TRỢ',1280,1160,340,['PK  Mã đánh giá','FK  Mã khách hàng','FK  Mã phiên hoặc yêu cầu','Loại đối tượng','Số sao','Nhận xét','Ngày đánh giá']],

 ['knowledge','TÀI LIỆU TRI THỨC',1280,760,360,['PK  Mã tài liệu','FK  Người quản lý','Tiêu đề','Nội dung nguồn','Loại tài liệu','Trạng thái xuất bản','Ngày tạo, cập nhật']],
 ['version','PHIÊN BẢN TRI THỨC',1700,760,350,['PK  Mã phiên bản','FK  Mã tài liệu','Số phiên bản','Nội dung','Trạng thái','Thời gian tạo']],
 ['chunk','ĐOẠN TRI THỨC',2110,760,330,['PK  Mã đoạn','FK  Mã tài liệu','Thứ tự','Nội dung đoạn','Vector biểu diễn','Mô hình embedding']],
 ['citation','NGUỒN TRÍCH DẪN',1700,1160,350,['PK  Mã trích dẫn','FK  Mã tin nhắn','FK  Mã đoạn','Tiêu đề nguồn','Đoạn được sử dụng','Độ tương đồng']],
];

const R = [
 ['role','account'],['account','customer'],['account','audit'],['account','setting'],
 ['customer','chat'],['account','chat'],['chat','message'],['account','message'],['message','sentiment'],['message','suggestion'],
 ['chat','handover'],['account','handover'],['chat','summary'],
 ['category','ticket'],['customer','ticket'],['chat','ticket'],['ticket','assignment'],['account','assignment'],
 ['ticket','status'],['account','status'],['ticket','reply'],['account','reply'],['ticket','attachment'],['account','attachment'],
 ['customer','evaluation'],['chat','evaluation'],['ticket','evaluation'],['ticket','summary'],
 ['account','knowledge'],['knowledge','version'],['version','chunk'],['knowledge','chunk'],['message','citation'],['chunk','citation']
];

const core=new Set(['role','account','customer','audit','chat','message','sentiment','suggestion','handover','category','ticket','evaluation','knowledge','chunk']);
const EN={
 role:['ROLE',['PK  RoleId','RoleName','Description']],
 account:['USER ACCOUNT',['PK  UserId','FK  RoleId','FullName','Email','PhoneNumber','PasswordHash','Status']],
 customer:['CUSTOMER',['PK  CustomerId','FK  UserId','CustomerType','ContactInformation','Status']],
 audit:['AUDIT LOG',['PK  AuditLogId','FK  UserId','Action','TargetObject','CreatedAt','Details']],
 chat:['CHAT SESSION',['PK  SessionId','FK  CustomerId','FK  AssignedAgentId','StartedAt','EndedAt','Channel','Status']],
 message:['MESSAGE',['PK  MessageId','FK  SessionId','FK  SenderId','Content','SenderType','SentAt']],
 sentiment:['SENTIMENT ANALYSIS',['PK  SentimentId','FK  MessageId','SentimentLabel','SentimentScore','AnalyzedAt']],
 suggestion:['AI REPLY SUGGESTION',['PK  SuggestionId','FK  MessageId','DraftContent','ConfidenceScore','ReviewStatus','CreatedAt']],
 handover:['HANDOVER',['PK  HandoverId','FK  SessionId','FK  AssignedAgentId','Reason','Status','RequestedAt','AcceptedAt']],
 category:['TICKET CATEGORY',['PK  CategoryId','CategoryName','Description']],
 ticket:['SUPPORT TICKET',['PK  TicketId','FK  CustomerId','FK  SessionId','FK  CategoryId','Title','Content','Priority','Status','CreatedAt, ClosedAt']],
 evaluation:['SUPPORT EVALUATION',['PK  EvaluationId','FK  CustomerId','FK  SessionId or TicketId','TargetType','Rating','Comment','EvaluatedAt']],
 knowledge:['KNOWLEDGE DOCUMENT',['PK  DocumentId','FK  ManagedBy','Title','SourceContent','DocumentType','PublicationStatus','CreatedAt, UpdatedAt']],
 chunk:['KNOWLEDGE CHUNK',['PK  ChunkId','FK  DocumentId','ChunkOrder','ChunkContent','EmbeddingVector','EmbeddingModel']]
};
const tables=T.filter(([id])=>core.has(id)).map(([id,name,x,y,w,cols])=>{const e=EN[id];return {id,name:e[0],x,y,w,cols:e[1],h:62+e[1].length*25}});
const relations=R.filter(([a,b])=>core.has(a)&&core.has(b));
const M=Object.fromEntries(tables.map(t=>[t.id,t]));
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;');

function edge(a,b,i){
 const A=M[a],B=M[b], ax=A.x+A.w/2, ay=A.y+A.h/2, bx=B.x+B.w/2, by=B.y+B.h/2;
 let p1,p2,d;
 if(Math.abs(ax-bx)>Math.abs(ay-by)){
   p1=ax<bx?[A.x+A.w,ay]:[A.x,ay]; p2=ax<bx?[B.x,by]:[B.x+B.w,by];
   const mx=(p1[0]+p2[0])/2+((i%7)-3)*5; d=`M${p1[0]} ${p1[1]}H${mx}V${p2[1]}H${p2[0]}`;
 } else {
   p1=ay<by?[ax,A.y+A.h]:[ax,A.y]; p2=ay<by?[bx,B.y]:[bx,B.y+B.h];
   const my=(p1[1]+p2[1])/2+((i%7)-3)*5; d=`M${p1[0]} ${p1[1]}V${my}H${p2[0]}V${p2[1]}`;
 }
 return `<path class="rel" d="${d}" marker-start="url(#one)" marker-end="url(#many)"/>`;
}

function table(t){
 const rows=t.cols.map((c,i)=>`<text x="14" y="${76+i*25}" class="${c.startsWith('PK')?'pk':c.startsWith('FK')?'fk':'f'}">${esc(c)}</text>`).join('');
 return `<g transform="translate(${t.x} ${t.y})"><rect class="box" width="${t.w}" height="${t.h}"/><path class="head" d="M0 0H${t.w}V46H0Z"/><text x="14" y="30" class="name">${esc(t.name)}</text>${rows}</g>`;
}

const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="2500" height="1560" viewBox="0 0 2500 1560"><defs><style>
.box{fill:#f5f5f5;stroke:#858585;stroke-width:1.4}.head{fill:#e1e1e1;stroke:#858585;stroke-width:1.4}.name{font:700 18px Arial,sans-serif;fill:#111}.f{font:15px Arial,sans-serif;fill:#222}.pk{font:700 15px Consolas,monospace;fill:#a96600}.fk{font:700 15px Consolas,monospace;fill:#1565c0}.rel{fill:none;stroke:#666;stroke-width:1.45}</style>
<marker id="one" viewBox="0 0 12 12" refX="6" refY="6" markerWidth="8" markerHeight="8" orient="auto"><path d="M6 0V12" stroke="#555" stroke-width="2"/></marker><marker id="many" viewBox="0 0 12 12" refX="7" refY="6" markerWidth="9" markerHeight="9" orient="auto"><path d="M11 1L2 6L11 11M2 0V12" fill="none" stroke="#555" stroke-width="1.7"/></marker></defs><rect width="2500" height="1560" fill="#fff"/>${relations.map((r,i)=>edge(r[0],r[1],i)).join('')}${tables.map(table).join('')}</svg>`;

fs.writeFileSync('docs/diagrams/erd-vietincare-ai-english.svg',svg,'utf8');
sharp(Buffer.from(svg)).png().toFile('docs/diagrams/erd-vietincare-ai-english.png').then(x=>console.log(JSON.stringify(x)));
