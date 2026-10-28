$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root=$PWD.Path
foreach($name in @('02_ban2.docx','03_ban2.docx','04_ban1.docx')) {
 $z=[IO.Compression.ZipFile]::Open((Join-Path $root $name),'Update')
 try {
  $entry=$z.GetEntry('word/document.xml');$reader=[IO.StreamReader]::new($entry.Open());[xml]$x=$reader.ReadToEnd();$reader.Dispose()
  $ns=[Xml.XmlNamespaceManager]::new($x.NameTable);$uri='http://schemas.openxmlformats.org/wordprocessingml/2006/main';$ns.AddNamespace('w',$uri)
  function TextOf($p){return (($p.SelectNodes('.//w:t',$ns)|ForEach-Object{$_.InnerText}) -join '')}
  function SetText($p,$s){$ts=@($p.SelectNodes('.//w:t',$ns));if($ts.Count){$ts[0].InnerText=$s;for($j=1;$j -lt $ts.Count;$j++){$ts[$j].InnerText=''}}}
  $ps=@($x.SelectNodes('//w:p',$ns))
  foreach($p in $ps) {
   $s=TextOf $p
   $s=$s.Replace('Username và Password','Email và mật khẩu').Replace('Sai User name/Password','Sai email/mật khẩu')
   $s=$s.Replace('mới2. AI Copilot','mới. 2. AI Copilot').Replace('(Online) theo tiêu chí phù hợp3.','(Online) theo tiêu chí phù hợp. 3.')
   $s=$s.Replace('Biểu đồ trình tự','Luồng trao đổi').Replace('Biểu đồ hoạt động','Luồng hoạt động').Replace('Biểu đồ trạng thái','Luồng xử lý')
   if($s -match '^Hình '){$s=$s.Replace('Hình ','Luồng ')}
   if($s.Trim() -eq 'Mô hình lớp (Class Diagram)'){$s='Mô hình lớp và ánh xạ dữ liệu bằng văn bản'}
   if($s -match '^3.1.\s+Sơ đồ thực thể'){$s='3.1 Quan hệ dữ liệu MySQL bằng văn bản'}
   if($s -match '^Ticket đang ở trạng thái'){$s='Ticket ở trạng thái Đã giải quyết; người thực hiện có quyền đóng ticket.'}
   if($s -eq 'Thông tin tương tác được cập nhật thành công.'){$s='Bản đính chính được lưu kèm tác giả và thời gian; không ghi đè lịch sử đã gửi.'}
   if($s -eq 'Cập nhật thông tin của một tương tác khi cần thiết.'){$s='Ghi đính chính tương tác, giữ nguyên bản gốc và audit log.'}
   if($s -match '^1. Tìm tương tác →'){$s='1. Tìm tương tác → 2. Kiểm tra quyền → 3. Thêm bản đính chính → 4. Ghi người sửa/thời gian → 5. Lưu MySQL.'}
   if($s -match '^Thêm, sửa, xóa hoặc cập nhật thông tin nhân viên'){$s='Tạo, sửa hoặc khóa tài khoản nhân viên; giữ dữ liệu lịch sử.'}
   $s=$s.Replace('Thêm/sửa/xóa nhân viên','Tạo/sửa/khóa nhân viên')
   if($s -eq 'Admin đã đăng nhập và khoảng thời gian hợp lệ.'){$s='Supervisor đã đăng nhập và khoảng thời gian hợp lệ; backend kiểm tra quyền báo cáo.'}
   if($s -match '^1. Chọn khoảng thời gian →'){$s='1. Supervisor chọn khoảng thời gian → 2. Truy vấn MySQL → 3. Tổng hợp ticket theo trạng thái/chủ đề, số phiên và CSAT → 4. Hiển thị; không có đánh giá thì báo Chưa có dữ liệu.'}
   if($s -eq 'Quản lý nhân viên, tài khoản và báo cáo hệ thống'){$s='Quản lý nhân viên, tài khoản, tri thức, cấu hình và audit log; báo cáo thuộc Supervisor.'}
   if($s -eq 'Một phiên hội thoại có thể nhận nhiều lượt đánh giá'){$s='Một phiên kết thúc có tối đa một đánh giá của chủ sở hữu.'}
   if($s -eq 'Một Ticket có thể nhận nhiều lượt đánh giá'){$s='Một ticket đóng có tối đa một đánh giá của chủ sở hữu.'}
   if($s -eq 'Bản băm mật khẩu tại UserAccount; Admin là vai trò, không có bảng mật khẩu riêng.'){$s='trangThai'}
   if($s -eq 'Mật khẩu'){$s='Bản băm mật khẩu tại UserAccount'}
   if($s -match '^2.5.1.\s+Phương thức: luuTuongTac'){$s='2.5.1 Thuộc tính'}
   if($s -eq 'Cho phép Quản trị viên thêm, sửa, xóa các bộ câu hỏi FAQ, chính sách lãi suất, chương trình khuyến mãi.'){$s='Admin tạo, sửa bản nháp và ngừng xuất bản FAQ/văn bản; giữ phiên bản nguồn đã được trích dẫn.'}
   if($s -eq 'Báo cáo & Dashboard' -or $s -match '^Cung cấp thông tin báo cáo'){$s=$s.Replace('theo thời gian thực','khi tải hoặc làm mới trang')}
   if($s -eq '1a: Khách hàng bỏ qua: Tắt biểu mẫu đánh giá sau 60 giây không thao tác'){$s='1a. Khách bỏ qua: không tạo đánh giá; có thể quay lại nếu chưa đánh giá mục tiêu này.'}
   SetText $p $s
  }
  # Synchronize attribute data types and relationship cardinalities in table rows.
  foreach($row in $x.SelectNodes('//w:tr',$ns)) {
   $cells=@($row.SelectNodes('w:tc',$ns))
   if($cells.Count -ge 3) {
    $a=(($cells[0].SelectNodes('.//w:t',$ns)|ForEach-Object{$_.InnerText}) -join '').Trim()
    $b=(($cells[1].SelectNodes('.//w:t',$ns)|ForEach-Object{$_.InnerText}) -join '').Trim()
    if($b -eq 'INT'){SetText $cells[2] '-'}
    if($a -match '^(ChatSession|Ticket) – Evaluation$'){SetText $cells[1] '1 – 0..1'}
    if($a -eq 'maTicket' -and $name -eq '04_ban1.docx' -and $cells.Count -ge 4){SetText $cells[3] 'Mã ticket; với chat độc lập dùng MaSession thay vì bắt buộc tạo ticket.'}
   }
   foreach($height in @($row.SelectNodes('w:trPr/w:trHeight',$ns))){[void]$height.ParentNode.RemoveChild($height)}
  }
  # Give the title an explicit title style; avoid retained blue borders.
  $first=$ps[0];$pr=$first.SelectSingleNode('w:pPr',$ns)
  if(!$pr){$pr=$x.CreateElement('w','pPr',$uri);[void]$first.PrependChild($pr)}
  foreach($node in @($pr.SelectNodes('w:pBdr|w:pStyle',$ns))){[void]$pr.RemoveChild($node)}
  $sty=$x.CreateElement('w','pStyle',$uri);$sty.SetAttribute('val',$uri,'Title');[void]$pr.PrependChild($sty)
  # Place scope notice up front without removing the existing author information.
  $body=$x.SelectSingleNode('//w:body',$ns)
  $intro=$x.CreateElement('w','p',$uri);$r=$x.CreateElement('w','r',$uri);$t=$x.CreateElement('w','t',$uri)
  $t.InnerText='Phiên bản 1.1 ngày 21/09/2026. Phạm vi: web VI/EN, bốn vai trò, chat RAG và ticket; MySQL 8.0.46 là hệ quản trị duy nhất. Yêu cầu triển khai và tiêu chí nghiệm thu theo PROJECT_SCOPE.md; chức năng hiện tại vẫn là demo.'
  [void]$r.AppendChild($t);[void]$intro.AppendChild($r);[void]$body.InsertAfter($intro,$body.FirstChild)
  if($name -eq '04_ban1.docx') {
   $extra=@(
    'Bổ sung thiết kế Supervisor và ánh xạ lớp',
    'Supervisor dùng UserAccount với Role Supervisor; thuộc tính maUser INT, hoTen, email, trangThai. phanCongTicket(maTicket, maAgent) kiểm tra vai trò, năng lực và trạng thái rồi ghi phân công/lịch sử MySQL. xemBaoCao(tuNgay, denNgay) tổng hợp ticket, phiên và CSAT. Agent và Admin cũng là vai trò của UserAccount, không phải bảng tài khoản riêng.',
    'Interaction là lớp dịch vụ cho hai loại tương tác: Message gắn ChatSession, TicketReply gắn Ticket. Lưu/xem tương tác nhận loại mục tiêu cùng MaSession hoặc MaTicket, không buộc chat phải có ticket. Kiểm tra chủ sở hữu hoặc Agent được giao trước mọi thao tác. TicketReply và định danh tài khoản gửi cần migration.',
    'Thiết kế đích bổ sung: Customer.MaUser UNIQUE FK UserAccount; TicketReply; TicketStatusHistory; MessageSource liên kết Message với KnowledgeChunk và phiên bản nguồn; SystemSetting lưu tham số không chứa bí mật. Bổ sung lưu phiên trong MySQL nếu dùng phiên server. Chi tiết tại PROJECT_SCOPE.md; SQL hiện tại chưa có các cấu trúc này.',
    'AI là dịch vụ backend, không phải một hệ quản trị. Các kiểu String ở mô hình lớp ánh xạ VARCHAR/LONGTEXT theo SQL; khóa nội bộ INT, ngày giờ DATETIME(3) UTC. DoTinCayAI/DoTinCay nếu sử dụng là điểm kỹ thuật có định nghĩa, không diễn giải là xác suất đúng khi chưa hiệu chỉnh.'
   )
   foreach($s in $extra){$p=$x.CreateElement('w','p',$uri);$r=$x.CreateElement('w','r',$uri);$t=$x.CreateElement('w','t',$uri);$t.InnerText=$s;[void]$r.AppendChild($t);[void]$p.AppendChild($r);[void]$body.InsertBefore($p,$body.SelectSingleNode('w:sectPr',$ns))}
  }
  $entry.Delete();$writer=[IO.StreamWriter]::new($z.CreateEntry('word/document.xml').Open(),[Text.UTF8Encoding]::new($false));$x.Save($writer);$writer.Dispose()
  Write-Output "$name refined"
 }finally{$z.Dispose()}
}
