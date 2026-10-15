/* runner.exe: LoadLibraryA a pack-extractor DLL and call RunExtractor(dir) */
#include <windows.h>
#include <stdio.h>
typedef void (*RunExtractorFunc)(const char*);
int main(int argc, char** argv) {
    HMODULE h;
    RunExtractorFunc f;
    if (argc < 3) { printf("usage: runner.exe <dll> <targetDir>\n"); return 1; }
    h = LoadLibraryA(argv[1]);
    if (!h) { printf("LoadLibraryA(%s) failed err=%lu\n", argv[1], GetLastError()); return 2; }
    f = (RunExtractorFunc)(void*)GetProcAddress(h, "RunExtractor");
    if (!f) { printf("no RunExtractor in %s\n", argv[1]); return 3; }
    printf("calling RunExtractor(%s)\n", argv[2]);
    f(argv[2]);
    printf("done\n");
    return 0;
}
