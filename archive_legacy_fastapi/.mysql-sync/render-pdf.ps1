$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
[void][Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
function Await($operation,$type) {
 $method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
 $task=$method.MakeGenericMethod($type).Invoke($null,@($operation));$task.Wait();return $task.Result
}
function AwaitAction($action) {
 $method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and !$_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
 $task=$method.Invoke($null,@($action));$task.Wait()
}
foreach($pdf in Get-ChildItem .doc-qa -Filter *.pdf) {
 $file=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($pdf.FullName)) ([Windows.Storage.StorageFile])
 $doc=Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
 $out=Join-Path $pdf.DirectoryName $pdf.BaseName;[void][IO.Directory]::CreateDirectory($out)
 for($i=0;$i -lt $doc.PageCount;$i++){
  $page=$doc.GetPage($i);$stream=[Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
  $options=[Windows.Data.Pdf.PdfPageRenderOptions]::new();$options.DestinationWidth=1200
  AwaitAction ($page.RenderToStreamAsync($stream,$options))
  $stream.Seek(0);$input=[System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
  $dest=[IO.File]::Create((Join-Path $out ('page-'+($i+1)+'.png')));$input.CopyTo($dest);$dest.Dispose();$input.Dispose();$stream.Dispose();$page.Dispose()
 }
 Write-Output ($pdf.Name+': '+$doc.PageCount+' PNG pages')
}
