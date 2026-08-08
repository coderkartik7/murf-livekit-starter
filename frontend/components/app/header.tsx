import Image from 'next/image';

export function Header() {
  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 md:px-8 h-[64px] bg-[#F0E4D3]"
      style={{
        borderBottom: '2px solid #1A1512',
      }}
    >
      <div className="flex items-center gap-3">
        <Image
          src="/logo.png"
          alt="DukaanMitra Logo"
          width={36}
          height={36}
          className="object-contain w-8 h-8 md:w-9 md:h-9"
          priority
        />
        <span
          className="font-serif font-bold text-xl md:text-2xl text-[#1A1512] tracking-tight"
          style={{ fontFamily: 'Georgia, serif' }}
        >
          DukaanMitra
        </span>
      </div>

      {/* Color Coded Status Dot */}
      <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#FFFDF9] border border-[#1A1512]/15 shadow-xs">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#7A8B69] opacity-75 motion-reduce:animate-none"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#7A8B69]"></span>
        </span>
        <span className="text-xs font-semibold text-[#1A1512]">Active</span>
      </div>
    </header>
  );
}
