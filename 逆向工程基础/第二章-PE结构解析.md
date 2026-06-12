---

## 第二章：PE 结构解析

### 2.1 什么是 PE 文件？

**PE = Portable Executable（可移植可执行文件）**

简单说：**Windows 上的 .exe / .dll / .sys 都是 PE 文件。**

就像你们产线上的每个产品都要有 BOM 表（物料清单），PE 文件也有自己的"清单"告诉 Windows：我由哪些部分组成、代码在哪、数据在哪、要调用哪些系统功能。

---

### 2.2 PE 文件的三明治结构

```ascii
┌───────────────────────────────────────────┐
│              DOS MZ 头 (64B)               │  ← 开头 "MZ"，e_lfanew 指向NT头
├───────────────────────────────────────────┤
│              DOS Stub                      │  ← DOS 下的兼容提示
├───────────────────────────────────────────┤
│              NT 头                          │  ← ★★★ 核心！
│  ┌─────────────────────────────────────┐  │
│  │  Signature ("PE\\0\\0")             │  │
│  │  FileHeader → Machine/SectionsNum   │  │
│  │  OptionalHeader → EntryPoint/IAT    │  │
│  └─────────────────────────────────────┘  │
├───────────────────────────────────────────┤
│              节区表 (Section Table)         │  ← 目录索引
├───────────────────────────────────────────┤
│  ┌───────────────────────────────────┐    │
│  │  .text  (代码段) ★★★              │    │  ← 可读+可执行，代码在这
│  ├───────────────────────────────────┤    │
│  │  .data  (数据段)                  │    │  ← 全局变量
│  ├───────────────────────────────────┤    │
│  │  .rdata (只读数据) ★★            │    │  ← 字符串、导入表
│  ├───────────────────────────────────┤    │
│  │  .idata (导入表) ★★★             │    │  ← ★ 调了哪些 DLL 函数
│  ├───────────────────────────────────┤    │
│  │  .rsrc  (资源)                    │    │  ← 图标、对话框、字符串表
│  └───────────────────────────────────┘    │
│           实际数据 (Raw Data)              │
└───────────────────────────────────────────┘
```

> **🖥️ 类比：** 就像你们开线的 **设备SOP手册**：
> - DOS 头 = 封面（写着"这是操作手册"）
> - NT 头 = 目录页（告诉你在哪页找什么）
> - 节区表 = 章节索引
> - .text = 第1章：操作步骤（代码本身）
> - .data = 第2章：物料清单（数据）
> - .idata = 附录：要借什么工具（调用外部函数）

---

### 2.3 ★★ 三个关键字段详解

**这是主人提问的第一个重点：为什么逆向者一打开 PE 文件，先看这三个字段？**

#### ① Machine — CPU 架构

```c
// IMAGE_FILE_HEADER 结构中的第一个字段
typedef struct _IMAGE_FILE_HEADER {
    WORD   Machine;              // CPU 架构
    WORD   NumberOfSections;     // 节区数量
    DWORD  TimeDateStamp;        // 编译时间戳
    DWORD  SizeOfOptionalHeader; // Optional Header 的大小
    WORD   Characteristics;      // 文件属性
} IMAGE_FILE_HEADER;
```

**常见值**：
| Machine 值 | 含义 | 逆向影响 |
|:-----------|:-----|:---------|
| `0x14C` | x86（32位） | 用 **x32dbg**、IDA32 |
| `0x8664` | x64（AMD64） | 用 **x64dbg**、IDA64 |
| `0x1C0` | ARM | 移动端/嵌入式 |
| `0xAA64` | ARM64 | Mac M芯片、新ARM设备 |

**为什么关心？——选错工具直接报错。**

```asm
; 32位反汇编
PUSH EBP               ; 参数压栈传递
MOV  EBP, ESP
SUB  ESP, 0x40

; 64位反汇编
PUSH RBP               ; 寄存器变 R 前缀
MOV  RBP, RSP
SUB  RSP, 0x40
; 前4个参数：RCX, RDX, R8, R9（用寄存器传！第5个才压栈）
```

**如果选错**：
```

打开 64 位 .exe 时：
  ✅ 用 x64dbg → 正常工作
  ❌ 用 x32dbg → 报错"不是有效的32位PE文件" → 白忙活

所以逆向的第一步不是双击，是看 Machine。
```

#### ② NumberOfSections — 节区数量

**为什么关心？——判断有没有被加壳。**

```
NumberOfSections 的规律：

正常 VC++ 编译的程序：4-6 个 → 直接反汇编
被 UPX 压缩的程序：   2 个   → 先脱壳
```

**同时看节区名**：

```
节区名 = 判断加壳类型的指纹：
.text .data .rdata .rsrc .reloc → 正常，标准 VC++
UPX0 UPX1                       → UPX 壳
.aspack/.packer                 → ASPack 壳（难度中等）
.themida                        → Themida 强壳（很难）
vmp0 vmp1                       → VMProtect（虚拟化保护，极难）
```

**为什么加壳只有 2 个节区？**

UPX 的工作方式是把所有代码和数据打包成一个压缩包，只留：
```
UPX0 = 壳的解压代码（加载时先运行这个）
UPX1 = 原程序的压缩数据（运行中解压出来）
```

所以逆向者看到 `NumberOfSections = 2`，第一反应是：**先脱壳，再看真正的结构。**

**权限异常也是线索**：
```
节区名: .text
Characteristics: 0xE0000020  ← 同时有可读+可写+可执行

正常的 .text 只有可读+可执行，不可写
如果可写 → 说明代码会运行时自己修改自己（加壳或恶意软件）
```

#### ③ Characteristics — 文件属性

**为什么关心？——判断是 EXE 还是 DLL。**

```c
// Characteristics 是一个16位的位图，每位代表一个属性
#define IMAGE_FILE_DLL             0x2000  // 第13位
#define IMAGE_FILE_SYSTEM          0x1000  // 系统文件
#define IMAGE_FILE_EXECUTABLE_IMAGE 0x0002 // 可执行
#define IMAGE_FILE_32BIT_MACHINE    0x0100 // 32位
```

**判断逻辑**：
```c
if (Characteristics & 0x2000) {
    // 这是 DLL
} else {
    // 这是 EXE（或驱动）
}
```

**EXE vs DLL 的调试方式完全不同**：
```
EXE 调试：
  x64dbg → 文件 → 打开（Open）
  → 断在入口点 AddressOfEntryPoint
  → 从 WinMain / main 开始分析

DLL 调试：
  x64dbg → 文件 → 附加（Attach）
  → 选一个正在运行的进程
  → 让目标进程加载这个 DLL
  → 在 DllMain 断下来
```

> **🖥️ 类比：**
> - **EXE = 整台设备**（有自己的电源开关、控制面板，独立运行）
> - **DLL = 一个功能模块**（比如视觉检测算法库，不能独立运行，要装到设备上才干活）

---

### 2.4 ★★ 节区（Section）概念详解

**这是主人提问的第二个重点：节区到底是什么？**

#### 一句话

**节区 = PE 文件里的"文件夹"，把不同类型的内容分开放。**

#### 为什么需要分节区？

**因为不同类型的内容需要不同的内存访问权限。**

```ascii
内存中的访问权限：
┌────────────────────────────────────────┐
│ .text（代码）→ 可读 + 可执行           │
│                 不可写                  │  ← 防止代码被修改
├────────────────────────────────────────┤
│ .data（变量）→ 可读 + 可写             │
│                 不可执行                │  ← 防止数据被当成代码执行
├────────────────────────────────────────┤
│ .rdata（常量）→ 只读                    │
│                 不可写、不可执行         │  ← 字符串不能改
└────────────────────────────────────────┘
```

**如果不分节区**，整个 PE 加载到内存只能统一设一种权限：
- 全可读写执行 → **病毒把代码写到变量区，电脑就凉了**
- 全只读 → **程序没法修改变量，跑不起来**
- 全可执行 → **浪费，字符串不需要执行权限**

#### 节区表的结构

每个节区对应一个 **IMAGE_SECTION_HEADER**（40字节）：

```c
typedef struct _IMAGE_SECTION_HEADER {
    BYTE  Name[8];            // 名字（.text / .data / .rdata）
    DWORD VirtualSize;        // 在内存中占多大
    DWORD VirtualAddress;     // 在内存中的起始地址（RVA）
    DWORD SizeOfRawData;      // 在文件中占多大
    DWORD PointerToRawData;   // 在文件中的起始位置（偏移量）
    DWORD Characteristics;    // 权限标志
} IMAGE_SECTION_HEADER;
```

**加载过程**：
```
文件（硬盘上）                   内存中
┌──────────────────┐         ┌──────────────────┐
│ .text             │         │ .text            │
│ PointerToRawData  │         │ VirtualAddress   │
│ = 0x400           │──复制──→│ = 0x1000         │
│ SizeOfRawData     │         │ VirtualSize      │
│ = 0x500           │         │ = 0x500          │
└──────────────────┘         └──────────────────┘
```

> **🖥️ 类比：** 节区表就像**领料单**：
> - `PointerToRawData` = 材料在仓库哪个货架（文件偏移）
> - `VirtualAddress` = 要送到产线哪个工位（内存地址）
> - `Size` = 这堆材料占多大地方

#### 常见节区一览

| 节区名 | 内容 | 内存权限 | 逆向意义 |
|:-------|:-----|:---------|:---------|
| **.text** | 程序代码 | 可读+可执行 | **加密狗验证代码就在这** |
| .data | 全局变量、静态变量 | 可读+可写 | 看有没有藏关键标志 |
| .rdata | 只读数据、字符串常量 | 只读 | **搜"加密狗""检测到"等字符串** |
| .idata | 导入表 | 可读+可写（运行时填地址） | **看调了哪些 DLL** |
| .rsrc | 资源（图标、菜单、对话框） | 只读 | 错误提示字符串可能藏在这 |
| .reloc | 重定位信息 | 可读+可写 | DLL 需要，EXE 一般没有 |

#### 不同编译器的节区名差异

| 编译器 | 代码节 | 数据节 |
|:-------|:-------|:-------|
| MSVC（Visual C++） | .text | .data .rdata |
| GCC/MinGW | .text | .data .rdata |
| Delphi | CODE | DATA |
| Go | .text | .noptrdata .data |

---

### 2.5 ★★ 导入表（Import Table）详解

**这是主人提问的第三个重点：导入表到底是什么？逆向者为什么最先看它？**

#### 一句话

**导入表 = 程序的「电话簿」。**

程序自己很多功能不会自己写，而是调用 Windows 现成的 API。导入表记录了：**"我要调哪些 DLL 的哪些函数"**。

#### 结构拆解

导入表是一个 **数组**，每个导入的 DLL 占一个条目，以全零条目结尾。

```c
typedef struct _IMAGE_IMPORT_DESCRIPTOR {
    DWORD OriginalFirstThunk;  // → 指向函数名/序号数组（原始备份）
    DWORD TimeDateStamp;       // 时间戳，一般=0
    DWORD ForwarderChain;      // 转发链，一般=0
    DWORD Name;                // → 指向 DLL 名字符串（如 "kernel32.dll"）
    DWORD FirstThunk;          // → 指向 IAT（导入地址表，运行时填地址）
} IMAGE_IMPORT_DESCRIPTOR;     // 共20字节
```

#### 为什么有两个看似重复的指针？

```
文件中（硬盘上）：
  OriginalFirstThunk → [函数名数组] → "CreateFileA", "DeviceIoControl", ...
  FirstThunk → [0, 0, 0, ...]    ← 占位，全是0

加载后（内存中）：
  OriginalFirstThunk → [函数名数组] → 还在，作为原始备份
  FirstThunk → [0x77665544, 0x7766AABB, ...] ← Windows 填入实际地址
```

**原始设计意图**：`FirstThunk` 指向的 IAT（导入地址表）被 Windows 用来快速填入函数地址，同时 `OriginalFirstThunk` 保留做备份。

#### 逆向者用导入表做什么？

**场景①：判断是否有加密狗**

```c
打开 .exe → 看导入表：

正常 DLL：
  kernel32.dll    ← 所有程序都有
  user32.dll      ← 所有 GUI 程序都有
  gdi32.dll       ← 绘图用

★ 可疑的 DLL（看到任何一个就是有加密狗）：
  sentinel.dll      ← SafeNet Sentinel 加密狗
  hasp_api.dll      ← HASP / Aladdin 加密狗
  hardlock.dll      ← Hardlock 加密狗
```

**场景②：判断是否跟硬件设备通信**

```c
kernel32.dll:
  → CreateFileA         // 打开文件或设备
  → DeviceIoControl     // 向设备发送控制码 ← 跟硬件通信！
  → CloseHandle         // 关闭设备
  → ReadFile / WriteFile
```

**vs 操作普通文件**：
```c
kernel32.dll:
  → CreateFileA
  → ReadFile / WriteFile
  → SetFilePointer
  → 没有 DeviceIoControl → 这是在操作文件，不是硬件
```

**场景③：一眼认出卖油（加壳）程序**

正常程序导入表：
```c
很多很多 DLL 和函数：
  kernel32.dll: CreateFileA, WriteFile, ReadFile, ...
  user32.dll: CreateWindowEx, MessageBoxA, ...
  gdi32.dll: TextOut, GetStockObject, ...
```

加壳后的程序导入表：
```c
kernel32.dll:
  → LoadLibraryA       // 加载 DLL
  → GetProcAddress     // 获取函数地址
  → VirtualProtect     // 修改内存保护属性

  只有这三条！→ 加壳了！
```

**为什么？**

```
加壳过程：
  原始程序（5MB）→ UPX 压缩 → 压缩包（2MB）
                                ↑
                    壳代码只有几百KB，负责解压

  壳代码需要的功能很少：
  - LoadLibraryA    → 加载程序真正需要的 DLL
  - GetProcAddress  → 找到 DLL 里的函数地址
  - VirtualProtect  → 修改内存权限，写入解压后的代码

  真正的导入表在压缩包里，运行解压后才看到。
```

> **🖥️ 类比：**
> 加壳就像把设备装箱运输：
> - 装箱后只贴了一张纸"开箱器 + 说明书"
> - 真正的工具全打包在箱子里
> - 逆向者看到的就是那几张纸（只有3个API）

#### 导入表在逆向流程中的位置

```
逆向一个 .exe 的工作流：

1️⃣ PE-bear / CFF Explorer 打开 .exe
2️⃣ 看导入表 → 有没有 sentinel.dll / hasp_api.dll？
3️⃣ 看 AddressOfEntryPoint（入口点）
4️⃣ 用 IDA Pro / Ghidra 反汇编
5️⃣ 从入口点开始，找 CALL CheckDog 的地方
6️⃣ 找到 CMP + JE/JNE → 修改跳转 → 破解！

第2步是最快的筛选手段，
3秒就能判断这个软件有没有加密狗。
```

---

### 2.6 实战：用 PE 结构找加密狗验证代码

```
Step 1️⃣ 查看导入表
  → PE-bear 打开 target.exe
  → 点 Directories → Import Table
  → 看到 sentinel.dll ← 有加密狗！

Step 2️⃣ 记录可疑函数
  → SENTINEL_Open()
  → SENTINEL_Login()
  → SENTINEL_Read()
  → SENTINEL_Close()

Step 3️⃣ 用 IDA Pro 打开
  → 跳转到入口点（AddressOfEntryPoint）
  → 搜索 "SENTINEL_Login"（Import → Name）
  → 双击 → 跳到使用它的代码

Step 4️⃣ 分析验证逻辑
  → CALL SENTINEL_Login  ← 调用狗验证
  → TEST EAX, EAX         ← 检查返回值
  → JE fail_label          ← 如果=0，跳失败处理
  → JMP continue_label    ← 如果≠0，正常继续

Step 5️⃣ 破解
  把 JE 改成 JMP（永远跳转到正常流程）
  或者把 JMP 改成 NOP（不跳，顺序执行到正常流程）
```

---

### 2.7 本章小结

| 知识点 | 要点 |
|:-------|:------|
| **PE 文件** | .exe / .dll / .sys 都是 PE 文件 |
| **DOS 头** | 开头 "MZ"，e_lfanew 指向 NT 头 |
| **NT 头** | 含 FileHeader + OptionalHeader |
| **Machine** | 0x14C=32位, 0x8664=64位 → 选调试器 |
| **NumberOfSections** | 4-6 正常，2 被加壳 |
| **Characteristics** | 0x2000 = DLL |
| **节区** | .text(代码), .data(变量), .rdata(字符串), .idata(导入表) |
| **导入表** | 程序的电话簿，看它知道调了哪些 API |
| **加壳判断** | 导入表只有3条 → 被加壳了 |
| **逆向流程** | 导入表 → 入口点 → 反汇编 → CMP+JE → 修改 |
