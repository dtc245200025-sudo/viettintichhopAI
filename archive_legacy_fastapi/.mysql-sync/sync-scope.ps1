$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root = Split-Path $PSScriptRoot -Parent
$backup = Join-Path $PSScriptRoot 'scope-before-2026-09-21.zip'
if (Test-Path -LiteralPath $backup) { throw 'Backup already exists; do not overwrite or rerun blindly.' }
$archive = [IO.Compression.ZipFile]::Open($backup, 'Create')
foreach ($name in @('02_ban2.docx','03_ban2.docx','04_ban1.docx','README.md','PROJECT_CHECKLIST.md')) {
    [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive,(Join-Path $root $name),$name)
}
$archive.Dispose()
$performance = 'Mục tiêu nghiệm thu: p95 thời gian từ gửi câu hỏi đến nhận đủ câu trả lời không quá 5 giây trên 50 câu hỏi, 5 phiên đồng thời, tối đa 1.000 đoạn tri thức. Ghi cấu hình máy, mô hình, mạng và tỷ lệ lỗi; chưa có kết quả đo.'
$common = @(
 'Phạm vi thống nhất phiên bản 1.1 ngày 21 tháng 09 năm 2026',
 'VietinCare AI là đồ án web hỗ trợ khách hàng bằng tiếng Việt và tiếng Anh. Các chức năng dưới đây là yêu cầu cần triển khai; hiện project có frontend demo và script SQL, chưa có backend hoặc AI hoạt động thực tế.',
 'MySQL Community Server 8.0.46 là hệ quản trị duy nhất; InnoDB, utf8mb4, database QLKHViettin. Dữ liệu nghiệp vụ, phiên, nhật ký, tri thức và embedding đều lưu trong MySQL. Không bổ sung hệ quản trị hoặc kho vector khác. Backend xử lý nghiệp vụ, gọi mô hình AI và tính độ tương đồng; MySQL không tự sinh câu trả lời.',
 'Phạm vi cốt lõi: đăng ký/đăng nhập/đăng xuất; bốn vai trò Customer, Agent, Supervisor, Admin; chat RAG có nguồn; lưu lịch sử; tạo và xử lý ticket; phân loại và cảm xúc; chuyển giao; đánh giá CSAT; quản lý FAQ/tri thức; dashboard cơ bản; audit log và cấu hình không chứa bí mật.',
 'Giai đoạn mở rộng: UC008 Copilot và UC009 tóm tắt; tải PDF/DOCX; tệp đính kèm ticket; OTP/SSO, quên mật khẩu qua email; NPS; xuất Excel/PDF; tích hợp SMS/email, Core Banking/CRM, iPay/eFAST, Voicebot, sinh trắc học và định tuyến VIP. Các mục này không là điều kiện nghiệm thu bản cốt lõi.',
 'Kiến trúc triển khai: một ứng dụng backend chia module và một MySQL. Không yêu cầu microservices, Kubernetes, GPU riêng, 5.000 phiên hay cam kết uptime 99,9%. Dùng dữ liệu giả lập; không tra cứu số dư, thực hiện giao dịch hoặc khóa thẻ thật.',
 'Khách hàng đăng nhập trước khi chat, tạo ticket hoặc xem lịch sử. FAQ công khai có thể đọc không cần đăng nhập; chat khách vãng lai nằm ngoài bản cốt lõi. Customer chỉ xem dữ liệu của mình; Agent xử lý ca được giao; Supervisor giám sát và phân công; Admin quản lý tài khoản, tri thức và cấu hình.',
 'Chat không tự tạo ticket cho mọi tin nhắn. Tạo ticket khi khách hàng yêu cầu hoặc đồng ý theo dõi vấn đề chưa giải quyết. Chuỗi trạng thái ticket: Mới → Đang xử lý → Đã giải quyết → Đã đóng. Chỉ người có quyền được chuyển trạng thái; ghi người thực hiện và thời điểm. Mở lại ticket là phần mở rộng.',
 'Ưu tiên gồm Thấp, Trung bình, Cao, Khẩn cấp. Cảm xúc gồm Tích cực, Trung tính, Tiêu cực; không dùng cảm xúc làm trạng thái ticket. Agent được sửa nhãn AI. Khi AI lỗi hoặc không phân loại được, đưa về hàng chờ chung để Supervisor phân công.',
 'RAG: Admin nhập FAQ/văn bản, lưu KnowledgeBase ở Nháp; chia đoạn, tạo embedding JSON trong KnowledgeChunk; kiểm tra cùng mô hình và số chiều; thử câu hỏi rồi Xuất bản. Chỉ truy xuất bản đã xuất bản. Lưu và hiển thị nguồn tài liệu/đoạn cùng phản hồi. Không gọi cập nhật tri thức là tự huấn luyện mô hình.',
 'Điểm tương đồng cosine không phải xác suất câu trả lời đúng. Ngưỡng truy xuất phải được hiệu chỉnh bằng bộ câu hỏi có nhãn và lưu cấu hình. Không đủ nguồn hoặc lỗi mô hình: thông báo chưa có thông tin xác thực, đề nghị gặp Agent hoặc tạo ticket; không tự bịa câu trả lời.',
 'Handover có các trạng thái Chờ tiếp nhận, Đã tiếp nhận, Đã kết thúc, Đã hủy. Agent nhận được lịch sử; mỗi phiên chỉ có một lượt chuyển giao đang chờ hoặc đang xử lý. Khi không có Agent sẵn sàng, khách được thông báo và có thể tạo ticket.',
 'Đánh giá: chủ sở hữu gửi một lần cho một phiên chat đã kết thúc hoặc một ticket đã đóng. Mỗi đánh giá chỉ có một mục tiêu; số sao bắt buộc từ 1 đến 5. CSAT = số đánh giá 4–5 sao / tổng đánh giá hợp lệ × 100%; không có đánh giá thì hiển thị Chưa có dữ liệu. NPS chưa thu thập trong bản cốt lõi.',
 $performance,
 'Kiểm thử bắt buộc: đúng/sai mật khẩu; sai vai trò; truy cập dữ liệu khách khác; trạng thái không hợp lệ; gửi lặp; AI lỗi/thiếu nguồn; không có Agent; đánh giá lặp; dữ liệu còn sau tải lại. Dùng ít nhất 50 câu hỏi gán nhãn để báo cáo độ chính xác phân loại; không ghi Pass hay phần trăm khi chưa chạy.',
 'An toàn bản đồ án: băm mật khẩu, kiểm tra quyền tại backend, truy vấn tham số hóa, giới hạn thử đăng nhập, hết hạn phiên, che dữ liệu nhạy cảm, không lưu khóa API trong mã nguồn. HTTPS khi triển khai qua mạng. Sao lưu và thử khôi phục MySQL trên môi trường thử nghiệm. Không tuyên bố chứng nhận hoặc tuân thủ ngân hàng khi chưa được đánh giá.',
 'Đồng bộ triển khai: SQLQuery1.sql hiện có 15 bảng. Liên kết Customer–UserAccount, phản hồi ticket, lịch sử trạng thái, định danh người gửi, nguồn trả lời RAG và cấu hình là các thay đổi thiết kế cần migration; chưa tồn tại đầy đủ trong SQL hiện hành. Không chạy lại script khởi tạo trên database có dữ liệu.',
 'Tham chiếu phạm vi: PROJECT_SCOPE.md. Mốc 27/09/2026 giữ theo kế hoạch ban đầu, không phải cam kết chức năng đã hoàn thành. Kết quả triển khai và kiểm thử theo PROJECT_CHECKLIST.md.'
)
$maps = @{}
$maps['02_ban2.docx'] = @{
 0='Thu thập và làm rõ yêu cầu VietinCare AI'; 7='Tài liệu xác định phạm vi đồ án web hỗ trợ khách hàng, làm cơ sở cho đặc tả 03 và thiết kế 04. Áp dụng phạm vi phiên bản 1.1 và chỉ dùng MySQL.';
 16='Hỗ trợ giải đáp FAQ trên web, theo dõi yêu cầu bằng ticket và hỗ trợ nhân viên; nghiệm thu trong môi trường demo.';
 24='Website VietinCare AI trên desktop/mobile. iPay/eFAST và Voicebot là mở rộng.';25='Kênh web';
 28='Giải đáp FAQ về thẻ, tiền gửi, vay và iPay từ tài liệu đã xuất bản. Không cung cấp tỷ giá/lãi suất thời gian thực hoặc thực hiện giao dịch thật.';
 44='Bản cốt lõi hoạt động độc lập với MySQL; Core Banking, CRM, quản lý thẻ và SMS/email là mở rộng.';
 48='Đăng nhập, băm mật khẩu, kiểm tra vai trò/quyền sở hữu và che dữ liệu nhạy cảm. Chỉ dùng dữ liệu giả lập; sinh trắc học và giao dịch thật ngoài phạm vi.';
 52='AI Copilot là mở rộng UC008; Agent đọc, sửa và chủ động gửi gợi ý.';
 56='Dashboard cơ bản: ticket theo trạng thái/chủ đề, số phiên và CSAT từ dữ liệu thực; hiệu quả AI và chỉ số nâng cao là mở rộng.';
 60='Admin nhập FAQ/văn bản, kiểm tra và xuất bản; đoạn tri thức và embedding lưu trong MySQL. Tải PDF/DOCX là mở rộng.';
 68='Thông báo lỗi rõ ràng; chỉ xác nhận lưu khi MySQL ghi thành công. Cho phép thử lại với khóa chống gửi trùng; không hứa tự gửi lại khi chưa có cơ chế.';
 72='Đánh giá 1–5 sao sau khi phiên kết thúc hoặc ticket đóng; mỗi khách chỉ đánh giá một lần cho từng mục tiêu.';
 76=$performance;80='Ghi nhận câu hỏi thiếu nguồn để Admin duyệt và cập nhật FAQ, tạo lại embedding. Không tự huấn luyện lại mô hình.';81='Cập nhật tri thức RAG';
 84='Định tuyến VIP/RM là mở rộng; bản cốt lõi phân công theo hàng chờ và mức ưu tiên.';
 88='Lưu lịch sử chat, ticket và audit log trong MySQL phục vụ nghiệm thu; dùng dữ liệu giả lập. Chính sách lưu giữ khi vận hành thật cần được xác định riêng.';
 92='Nghiệm thu luồng đăng nhập → chat/ticket → Agent xử lý → đóng → đánh giá; kiểm thử quyền, ngoại lệ và lưu dữ liệu; đo hiệu năng theo mục tiêu chung.';
 98='Trò chuyện RAG qua Chat Widget trong môi trường demo sau đăng nhập.';101='Xác thực tài khoản để xem dữ liệu hỗ trợ của chính mình; không tra cứu số dư hoặc lịch sử giao dịch thật.';
 103='Tạo ticket khi khách yêu cầu hoặc đồng ý theo dõi; AI gợi ý chủ đề và ưu tiên, Agent được chỉnh sửa.';
 105='Mở rộng UC008: gợi ý câu trả lời cho Agent; không thuộc nghiệm thu cốt lõi.';
 108='Nhập FAQ/văn bản và tạo embedding trong MySQL cho RAG; tải PDF/DOCX là mở rộng, Excel ngoài bản cốt lõi.';
 110='Dashboard truy vấn dữ liệu MySQL khi tải/làm mới trang: ticket, phiên chat và CSAT.';112='Thống kê CSAT từ đánh giá 1–5 sao; NPS là mở rộng.';
 118=$performance;119='Kiểm thử 5 phiên đồng thời trong môi trường demo; ghi cấu hình và kết quả thực tế.';
 121='HTTPS khi triển khai qua mạng; mật khẩu được băm và bí mật đặt ngoài mã nguồn. Mã hóa ổ đĩa và vận hành ngân hàng là yêu cầu triển khai mở rộng.';
 122='Đồ án dùng dữ liệu giả lập, không tuyên bố đạt chứng nhận an toàn thông tin hoặc tuân thủ ngân hàng.';
 125='Không cam kết uptime sản xuất; kiểm tra xử lý lỗi và khả năng chạy lại ứng dụng demo.';
 126='Hướng dẫn sao lưu MySQL và kiểm thử khôi phục trên database thử nghiệm; sao lưu tự động là mở rộng.';
 128='Một backend chia module và MySQL duy nhất; không yêu cầu microservices hoặc Kubernetes.'
}
$maps['03_ban2.docx'] = @{
 0='Đặc tả yêu cầu VietinCare AI phiên bản 1.1';208='Một backend chia module, phục vụ web VI/EN và kết nối MySQL duy nhất; không yêu cầu cluster.';
 209='Mô hình AI được backend gọi qua giao diện dịch vụ; không yêu cầu GPU riêng. Nhà cung cấp/mô hình được chốt khi triển khai.';
 219='Core Banking/CRM và ứng dụng ngân hàng thật thuộc giai đoạn mở rộng; bản cốt lõi dùng dữ liệu giả lập.';
 220='Thông báo trong giao diện; SMS/email và OTP là mở rộng.';
 230='Customer, Agent, Supervisor và Admin đăng nhập bằng email/mật khẩu; backend xác thực và kiểm tra quyền. OTP/SSO là mở rộng.';
 238='3. Backend kiểm tra tài khoản hoạt động và đối chiếu mật khẩu băm.';239='4. Backend tạo phiên và ghi audit log.';240='5. Điều hướng đến giao diện theo vai trò.';
 243='2a. Phiên không hợp lệ/hết hạn: yêu cầu đăng nhập lại; không cấp quyền dựa trên giao diện.';
 264='Giải đáp câu hỏi từ tri thức đã xuất bản qua web trong môi trường demo.';
 277='1a. Không đủ nguồn theo ngưỡng đã hiệu chỉnh hoặc AI lỗi: thông báo chưa có thông tin xác thực và đề nghị gặp Agent/tạo ticket. Không mặc định dùng ngưỡng 70%.';
 306='2. Nhập Tiêu đề, Nội dung, Loại dịch vụ; tệp đính kèm thuộc mở rộng.';
 314='- Hiển thị mã ticket và xác nhận trong giao diện sau khi MySQL lưu thành công; email/SMS là mở rộng.';
 382='- Cảnh báo khi mức ưu tiên Khẩn cấp; cảm xúc và mức ưu tiên là hai trường riêng.';
 541='Thu thập mức hài lòng CSAT sau hỗ trợ; NPS là mở rộng.';
 552='4. Lưu đánh giá 1–5 sao, kiểm tra chủ sở hữu, trạng thái kết thúc và chống đánh giá lặp; cập nhật CSAT.';
 572='Quản lý FAQ/văn bản, chia đoạn và tạo embedding cho RAG trong MySQL; không huấn luyện lại mô hình.';
 582='3. Backend chia đoạn, tạo embedding và lưu JSON vào KnowledgeChunk trong MySQL.';
 644='Hiển thị số ticket theo trạng thái/chủ đề, số phiên chat và CSAT từ MySQL; NPS/SLA nâng cao là mở rộng.';
 653='4. Làm mới dữ liệu theo bộ lọc; xuất Excel/PDF là mở rộng.';
 721='2. Admin thay đổi ngưỡng truy xuất, thời gian chờ và cấu hình không chứa bí mật; khóa API đặt ngoài mã nguồn.';
 741='Dùng dữ liệu giả lập; băm mật khẩu, kiểm tra quyền backend và che dữ liệu nhạy cảm. Không tuyên bố chứng nhận an toàn ngân hàng.';
 745='Không cam kết uptime sản xuất; kiểm tra khả năng phục hồi và thông báo lỗi trong môi trường demo.';746=$performance
}
$maps['04_ban1.docx'] = @{
 0='Thiết kế hướng đối tượng VietinCare AI phiên bản 1.1';
 43='maUser';44='INT';45='-';46='Tham chiếu UserAccount; cần bổ sung liên kết bằng migration, mật khẩu băm chỉ lưu ở UserAccount.';
 68='1. Kiểm tra dữ liệu và email duy nhất → 2. Băm mật khẩu → 3. Tạo UserAccount vai trò Customer và Customer trong một transaction MySQL → 4. Trả kết quả.';
 105='1. Nhận câu hỏi trong ChatSession → 2. Lưu Message → 3. Truy xuất tri thức MySQL → 4. Trả lời có nguồn → 5. Chỉ tạo Ticket khi khách yêu cầu hoặc đồng ý.';
 103='Kết quả chat hoặc maTicket: INT khi có tạo ticket.';
 109='Tin nhắn được lưu; nếu tạo ticket thì trạng thái khởi tạo là Mới.';
 110='2.1.5 Phương thức xemLichSu';
 126='Danh sách ticket và lịch sử thuộc khách hàng đăng nhập được trả về.';
 184='1. Kiểm tra khách hàng và quyền → 2. Kiểm tra nội dung → 3. Tạo Ticket trạng thái Mới → 4. Lưu MySQL → 5. Phân loại; lỗi AI vẫn giữ ticket ở hàng chờ chung.';
 274='nguongTruyXuat';275='Float';276='-';277='Ngưỡng cosine được hiệu chỉnh trên bộ kiểm thử; không phải xác suất trả lời đúng.';
 373='1. Nhận yêu cầu handover cho phiên chat → 2. Lưu hàng chờ MySQL → 3. Agent tiếp nhận → 4. Hiển thị lịch sử; không có Agent thì đề nghị tạo ticket.';
 614='passwordHash';618='Bản băm mật khẩu tại UserAccount; Admin là vai trò, không có bảng mật khẩu riêng.';
 738='Khách hàng đăng nhập → ChatSession → Message → RAG dùng MySQL → Phản hồi có nguồn';
 742='Thiếu nguồn hoặc cần hỗ trợ → Handover hoặc Ticket theo lựa chọn khách hàng → Agent xử lý → Đóng → Đánh giá';
 744='Admin quản lý tài khoản, tri thức, cấu hình và log; Supervisor giám sát, phân công và xem báo cáo.'
}
$flows = @{
 'UC001'='Người dùng → Email/mật khẩu → Backend xác thực MySQL → Phiên → Giao diện theo vai trò; sai thông tin → báo lỗi.';
 'UC002'='Customer đã đăng nhập → Message → Backend → KnowledgeChunk đã xuất bản trong MySQL → RAG → Phản hồi kèm nguồn; thiếu nguồn → đề nghị hỗ trợ.';
 'UC003'='Khách đồng ý tạo ticket → Kiểm tra quyền/dữ liệu → MySQL lưu trạng thái Mới → Hiển thị mã theo dõi.';
 'UC004'='Ticket mới → AI gợi ý chủ đề/ưu tiên → MySQL → Hàng chờ; không phân loại được → Supervisor.';
 'UC005'='Tin nhắn → AI → Tích cực/Trung tính/Tiêu cực → MySQL → Agent xem; ưu tiên là trường riêng.';
 'UC006'='Yêu cầu chuyển giao → Hàng chờ MySQL → Agent nhận → Lịch sử chat; không có Agent → đề nghị tạo ticket.';
 'UC007'='Ticket Mới → Agent nhận → Đang xử lý → Phản hồi → Đã giải quyết → Đã đóng; mọi bước kiểm tra quyền và ghi lịch sử.';
 'UC008'='Mở rộng: Tin nhắn → AI gợi ý → Agent sửa/duyệt → Gửi → MySQL.';
 'UC009'='Mở rộng: Kết thúc/chuyển giao → Đọc lịch sử MySQL → Tóm tắt → Lưu và hiển thị cho Agent.';
 'UC010'='Phiên kết thúc hoặc ticket đóng → Chủ sở hữu đánh giá một lần 1–5 sao → MySQL → CSAT.';
 'UC011'='Admin → FAQ/văn bản Nháp → Chia đoạn/embedding → MySQL → Thử câu hỏi → Xuất bản.';
 'UC012'='Admin → Kiểm tra quyền → Tạo/sửa/khóa tài khoản và vai trò → MySQL → AuditLog.';
 'UC013'='Supervisor → Bộ lọc → Truy vấn MySQL → Ticket/phiên/CSAT; chưa có đánh giá → Chưa có dữ liệu.';
 'UC014'='Thao tác nghiệp vụ → Backend ghi AuditLog MySQL → Admin lọc/xem; không cho sửa log qua giao diện.';
 'UC015'='Admin → Cấu hình không chứa bí mật → Kiểm tra giá trị → MySQL → AuditLog.'
}
function Set-Paragraph($p, [string]$text, $x, $ns) {
    $ts=@($p.SelectNodes('.//w:t',$ns))
    if($ts.Count) { $ts[0].InnerText=$text; for($j=1;$j -lt $ts.Count;$j++){$ts[$j].InnerText=''} }
    else { $r=$x.CreateElement('w','r',$ns.LookupNamespace('w'));$t=$x.CreateElement('w','t',$ns.LookupNamespace('w'));$t.InnerText=$text;[void]$r.AppendChild($t);[void]$p.AppendChild($r) }
}
foreach($name in $maps.Keys) {
    $path=Join-Path $root $name
    $z=[IO.Compression.ZipFile]::Open($path,'Update')
    try {
        $entry=$z.GetEntry('word/document.xml');$reader=[IO.StreamReader]::new($entry.Open());[xml]$x=$reader.ReadToEnd();$reader.Dispose()
        $ns=[Xml.XmlNamespaceManager]::new($x.NameTable);$ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
        $ps=@($x.SelectNodes('//w:p',$ns));$currentUC='';$imageCount=0
        for($i=0;$i -lt $ps.Count;$i++) {
            $p=$ps[$i];$s=($p.SelectNodes('.//w:t',$ns)|ForEach-Object{$_.InnerText}) -join ''
            if($s -match '(UC\d{3})'){$currentUC=$Matches[1]}
            if($maps[$name].ContainsKey($i)){$s=$maps[$name][$i]}
            $s=$s.Replace('Supervisonr','Supervisor').Replace('Chatbox','Chatbot').Replace('Knowledgge','Knowledge').Replace('Compilot','Copilot').Replace('Managemnet','Management').Replace('Trung lập','Trung tính').Replace('Chờ xử lý','Mới')
            $s=$s.Replace('CSAT/NPS','CSAT (NPS là mở rộng)').Replace('Quản lý Tài khoản','Cấu hình hệ thống').Replace('Quản lý Tài khoản','Cấu hình hệ thống')
            $s=$s.Replace('Khách hàng 24/7','Khách hàng trong môi trường demo').Replace('Hỗ trợ 24/7','Hỗ trợ trên web demo').Replace('Yêu cầu ≥ 99,9%','Không cam kết uptime sản xuất')
            $s=$s.Replace('Agent, AT Copilot','Agent, AI Copilot').Replace('Tích cực, Trung tính, Tiêu cực, Bức xúc cao','Tích cực, Trung tính, Tiêu cực')
            if($s -match '^4\. Nếu phát hiện cảm xúc'){$s='4. Nếu mức ưu tiên là Khẩn cấp, cảnh báo Supervisor; cảm xúc tiêu cực không tự quyết định mức ưu tiên.'}
            if($name -eq '03_ban2.docx') {
                if($s -eq 'Agent, Supervisor, Admin'){$s='Customer, Agent, Supervisor, Admin'}
                if($s -match '^Xác thực danh tính người dùng'){$s='Xác thực Customer, Agent, Supervisor và Admin trước khi truy cập chức năng được cấp quyền.'}
                if($s -match '^Khách hàng mở ứng dụng/website'){$s='Khách hàng đã đăng nhập và mở khung chat trên website.'}
                if($s -match '^2\. Admin tải tệp tài liệu mới'){$s='2. Admin nhập FAQ/văn bản; tải PDF/DOCX thuộc mở rộng.'}
                if($s -match '^Admin tải tài liệu nghiệp vụ'){$s='Admin nhập FAQ/văn bản để backend chia đoạn, tạo embedding và lưu MySQL; tải file là mở rộng.'}
                if($s -match 'qua Email/Giao diện'){$s=$s.Replace('qua Email/Giao diện hỗ trợ','qua giao diện hỗ trợ')}
                if($s -eq 'Theo dõi tài khoản ' -or $s.Trim() -eq 'Theo dõi tài khoản'){$s='Quản lý tham số vận hành không chứa bí mật'}
                if($s -match '^UC008_|^UC009_'){$s+=' (mở rộng)'}
            }
            if($name -eq '04_ban1.docx') {
                $s=$s.Replace('Mã hóa mật khẩu','Băm mật khẩu')
                $s=[regex]::Replace($s,'(maKH|maNV|maTicket|maTuongTac): String \(20\)','$1: INT')
                if($s.Trim() -eq 'String' -and $i -gt 0) {
                    $prior=($ps[$i-1].SelectNodes('.//w:t',$ns)|ForEach-Object{$_.InnerText}) -join ''
                    if($prior -match '^(maKH|maNV|maTicket|maTuongTac|maAdmin)$'){$s='INT'}
                }
            }
            if($s){Set-Paragraph $p $s $x $ns}
            $drawings=@($p.SelectNodes('.//w:drawing|.//w:pict',$ns))
            if($drawings.Count) {
                foreach($drawing in $drawings){[void]$drawing.ParentNode.RemoveChild($drawing)}
                $flow='Customer → Web VI/EN → Backend nghiệp vụ và AI → MySQL duy nhất. Agent xử lý hỗ trợ; Supervisor giám sát; Admin quản lý. Chat → Ticket khi cần → Xử lý → Đóng → CSAT.'
                if($name -eq '03_ban2.docx' -and $flows.ContainsKey($currentUC)){$flow=$flows[$currentUC]}
                if($name -eq '04_ban1.docx'){$flow='MySQL: Role 1–n UserAccount; Customer 1–n ChatSession và Ticket; ChatSession 1–n Message, Handover, ConversationSummary; Message 1–n SentimentAnalysis, AISuggestion; KnowledgeBase 1–n KnowledgeChunk; UserAccount 1–n KnowledgeBase, AuditLog. Liên kết tài khoản khách hàng và lịch sử/phản hồi ticket cần migration. AI là dịch vụ backend; Agent/Supervisor/Admin là vai trò UserAccount.'}
                Set-Paragraph $p ('Luồng và quan hệ phiên bản 1.1: '+$flow) $x $ns
                $imageCount++
            }
            if($s -match '^(Hình |Activity Diagram|Sequence Diagram|Acttivity Diagram|Actvity Diagram)') {
                Set-Paragraph $p ([regex]::Replace($s,'Biểu đồ trạng thái','Luồng xử lý').Replace('Activity Diagram','Luồng hoạt động').Replace('Sequence Diagram','Luồng trao đổi')) $x $ns
            }
        }
        $body=$x.SelectSingleNode('//w:body',$ns);$sect=$body.SelectSingleNode('w:sectPr',$ns)
        foreach($line in $common){$p=$x.CreateElement('w','p',$ns.LookupNamespace('w'));Set-Paragraph $p $line $x $ns;if($sect){[void]$body.InsertBefore($p,$sect)}else{[void]$body.AppendChild($p)}}
        $entry.Delete();$new=$z.CreateEntry('word/document.xml');$writer=[IO.StreamWriter]::new($new.Open(),[Text.UTF8Encoding]::new($false));$x.Save($writer);$writer.Dispose()
        Write-Output "$name : updated; $imageCount obsolete diagram placements replaced with editable version 1.1 flows"
    } finally {$z.Dispose()}
}
