import { NextRequest, NextResponse } from "next/server";
import { readFile, readdir, unlink, stat } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";

const DOWNLOAD_TTL_MS = parseInt(process.env.DOWNLOAD_TTL_MS || String(60 * 60 * 1000), 10); // 1 hour

async function cleanupExpiredDownloads() {
  const dir = tmpdir();
  try {
    const files = await readdir(dir);
    const now = Date.now();
    for (const file of files) {
      if (!file.startsWith("bidiq_")) continue;
      const filePath = join(dir, file);
      try {
        // Try timestamp from filename first (format: bidiq_{timestamp}_{uuid}.xlsx)
        const tsMatch = file.match(/^bidiq_(\d+)_/);
        if (tsMatch) {
          const createdAt = parseInt(tsMatch[1], 10);
          if (now - createdAt > DOWNLOAD_TTL_MS) {
            await unlink(filePath);
          }
          continue;
        }
        // Fallback to file mtime for legacy filenames
        const { mtimeMs } = await stat(filePath);
        if (now - mtimeMs > DOWNLOAD_TTL_MS) {
          await unlink(filePath);
        }
      } catch { /* file already deleted or inaccessible */ }
    }
  } catch { /* tmpdir read failed, skip cleanup */ }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json(
      { message: "ID obrigatório" },
      { status: 400 }
    );
  }

  // Lazy cleanup of expired downloads
  cleanupExpiredDownloads().catch(() => {});

  // Read from filesystem
  const tmpDir = tmpdir();
  const filePath = join(tmpDir, `bidiq_${id}.xlsx`);

  try {
    const buffer = await readFile(filePath);
    const filename = `descomplicita_${new Date().toISOString().split("T")[0]}.xlsx`;

    console.log(`✅ Download served: ${id} (${buffer.length} bytes)`);

    // Convert Buffer to Uint8Array for Next.js Response
    const uint8Array = new Uint8Array(buffer);

    return new NextResponse(uint8Array, {
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="${filename}"`
      }
    });
  } catch (error) {
    console.error(`❌ Download failed for ${id}:`, error);
    return NextResponse.json(
      { message: "Download expirado ou inválido. Faça uma nova busca para gerar o Excel." },
      { status: 404 }
    );
  }
}
