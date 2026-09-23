$ErrorActionPreference='Stop'
$root=$PWD.Path
$out=Join-Path $root '.doc-qa'
[void][IO.Directory]::CreateDirectory($out)
foreach($name in @('02_ban2.docx','03_ban2.docx','04_ban1.docx')) {
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false
 $word.DisplayAlerts=0
 try {
  $doc=$word.Documents.Open((Join-Path $root $name),$false,$true)
  try {
   $doc.Repaginate()
   $pdf=Join-Path $out ($name.Replace('.docx','.pdf'))
   $doc.ExportAsFixedFormat($pdf,17)
   Write-Output ($name+': pages='+$doc.ComputeStatistics(2))
  }finally{try{$doc.Close(0)}catch{Write-Output 'Word closed after export'} }
 }finally{try{$word.Quit()}catch{};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
}
