import svgPaths from "./svg-asca0xn6q3";

function Icon() {
  return (
    <div className="relative shrink-0 size-[20px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 20 20">
        <g id="Icon">
          <path d={svgPaths.p26ddc800} id="Vector" stroke="var(--stroke-0, #030213)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" style={{ stroke: "color(display-p3 0.0118 0.0078 0.0745)", strokeOpacity: "1" }} />
          <path d={svgPaths.p35ba4680} id="Vector_2" stroke="var(--stroke-0, #030213)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" style={{ stroke: "color(display-p3 0.0118 0.0078 0.0745)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Heading() {
  return (
    <div className="flex-[1_0_0] h-[28px] min-h-px min-w-px relative" data-name="Heading 1">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[28px] left-0 not-italic text-[#0a0a0a] text-[18px] top-[-1.22px] whitespace-nowrap">Biodiversity Risk Platform</p>
      </div>
    </div>
  );
}

function Container1() {
  return (
    <div className="h-[28px] relative shrink-0 w-[237.014px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center relative size-full">
        <Icon />
        <Heading />
      </div>
    </div>
  );
}

function Container() {
  return (
    <div className="h-[28px] relative shrink-0 w-[279.528px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-center relative size-full">
        <Container1 />
      </div>
    </div>
  );
}

function Icon1() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g clipPath="url(#clip0_4_1383)" id="Icon">
          <path d={svgPaths.p241f1490} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          <path d={svgPaths.p6b27c00} id="Vector_2" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          <path d={svgPaths.p312f7580} id="Vector_3" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_4_1383">
            <rect fill="white" height="16" style={{ fill: "white", fillOpacity: "1" }} width="16" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Text() {
  return (
    <div className="flex-[1_0_0] h-[20px] min-h-px min-w-px relative" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] text-center whitespace-nowrap">Configure Layers</p>
      </div>
    </div>
  );
}

function Button() {
  return (
    <button className="cursor-pointer h-[32px] relative rounded-[10px] shrink-0 w-[154.569px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center px-[12px] py-[6px] relative size-full">
        <Icon1 />
        <Text />
      </div>
    </button>
  );
}

function Header() {
  return (
    <div className="bg-white h-[56px] relative shrink-0 w-[1367.111px]" data-name="Header">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-center justify-between pb-[0.889px] px-[24px] relative size-full">
        <Container />
        <Button />
      </div>
    </div>
  );
}

function Heading1() {
  return (
    <div className="h-[30px] relative shrink-0 w-full" data-name="Heading 2">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[30px] left-0 not-italic text-[#0a0a0a] text-[20px] top-[-2.11px] whitespace-nowrap">Screened Suppliers</p>
    </div>
  );
}

function Paragraph() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">5 locations analyzed</p>
    </div>
  );
}

function Container3() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[86.889px] items-start left-0 pb-[0.889px] pt-[16px] px-[16px] top-0 w-[319.111px]" data-name="Container">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Heading1 />
      <Paragraph />
    </div>
  );
}

function Container7() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Great Ocean Dairy Co.</p>
    </div>
  );
}

function Container8() {
  return (
    <div className="content-stretch flex h-[20px] items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Medium',sans-serif] font-medium leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Otways, Victoria</p>
    </div>
  );
}

function Container6() {
  return (
    <div className="h-[44px] relative shrink-0 w-[263.111px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative size-full">
        <Container7 />
        <Container8 />
      </div>
    </div>
  );
}

function Icon2() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p19bc7f80} id="Vector" stroke="var(--stroke-0, #D4183D)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8314 0.0941 0.2392)", strokeOpacity: "1" }} />
          <path d="M8 6V8.66667" id="Vector_2" stroke="var(--stroke-0, #D4183D)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8314 0.0941 0.2392)", strokeOpacity: "1" }} />
          <path d="M8 11.3333H8.00667" id="Vector_3" stroke="var(--stroke-0, #D4183D)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8314 0.0941 0.2392)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Container5() {
  return (
    <div className="absolute content-stretch flex h-[44px] items-start justify-between left-[16px] top-[16px] w-[287.111px]" data-name="Container">
      <Container6 />
      <Icon2 />
    </div>
  );
}

function Text1() {
  return (
    <div className="bg-[#ececf0] h-[19.986px] relative rounded-[4px] shrink-0 w-[67.556px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start px-[8px] py-[2px] relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#0a0a0a] text-[12px] whitespace-nowrap">High Risk</p>
      </div>
    </div>
  );
}

function Text2() {
  return (
    <div className="h-[15.986px] relative shrink-0 w-[87.361px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">high confidence</p>
      </div>
    </div>
  );
}

function Container9() {
  return (
    <div className="absolute content-stretch flex gap-[8px] h-[19.986px] items-center left-[16px] top-[68px] w-[287.111px]" data-name="Container">
      <Text1 />
      <Text2 />
    </div>
  );
}

function Button1() {
  return (
    <div className="h-[104.875px] relative shrink-0 w-full" data-name="Button">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Container5 />
      <Container9 />
    </div>
  );
}

function Container12() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Gippsland Organic Farms</p>
    </div>
  );
}

function Container13() {
  return (
    <div className="content-stretch flex h-[20px] items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Medium',sans-serif] font-medium leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">East Gippsland, VIC</p>
    </div>
  );
}

function Container11() {
  return (
    <div className="h-[44px] relative shrink-0 w-[263.111px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative size-full">
        <Container12 />
        <Container13 />
      </div>
    </div>
  );
}

function Icon3() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p19bc7f80} id="Vector" stroke="var(--stroke-0, #D4183D)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8314 0.0941 0.2392)", strokeOpacity: "1" }} />
          <path d="M8 6V8.66667" id="Vector_2" stroke="var(--stroke-0, #D4183D)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8314 0.0941 0.2392)", strokeOpacity: "1" }} />
          <path d="M8 11.3333H8.00667" id="Vector_3" stroke="var(--stroke-0, #D4183D)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8314 0.0941 0.2392)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Container10() {
  return (
    <div className="absolute content-stretch flex h-[44px] items-start justify-between left-[16px] top-[16px] w-[287.111px]" data-name="Container">
      <Container11 />
      <Icon3 />
    </div>
  );
}

function Text3() {
  return (
    <div className="bg-[#ececf0] h-[19.986px] relative rounded-[4px] shrink-0 w-[67.556px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start px-[8px] py-[2px] relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#0a0a0a] text-[12px] whitespace-nowrap">High Risk</p>
      </div>
    </div>
  );
}

function Text4() {
  return (
    <div className="h-[15.986px] relative shrink-0 w-[108.014px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">medium confidence</p>
      </div>
    </div>
  );
}

function Container14() {
  return (
    <div className="absolute content-stretch flex gap-[8px] h-[19.986px] items-center left-[16px] top-[68px] w-[287.111px]" data-name="Container">
      <Text3 />
      <Text4 />
    </div>
  );
}

function Button2() {
  return (
    <div className="h-[104.875px] relative shrink-0 w-full" data-name="Button">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Container10 />
      <Container14 />
    </div>
  );
}

function Container17() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Murray Valley Produce</p>
    </div>
  );
}

function Container18() {
  return (
    <div className="content-stretch flex h-[20px] items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Medium',sans-serif] font-medium leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Swan Hill, Victoria</p>
    </div>
  );
}

function Container16() {
  return (
    <div className="h-[44px] relative shrink-0 w-[263.111px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative size-full">
        <Container17 />
        <Container18 />
      </div>
    </div>
  );
}

function Icon4() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g clipPath="url(#clip0_4_1379)" id="Icon">
          <path d={svgPaths.p34e03900} id="Vector" stroke="var(--stroke-0, #00A63E)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0000 0.6510 0.2431)", strokeOpacity: "1" }} />
          <path d={svgPaths.p1f2c5400} id="Vector_2" stroke="var(--stroke-0, #00A63E)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0000 0.6510 0.2431)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_4_1379">
            <rect fill="white" height="16" style={{ fill: "white", fillOpacity: "1" }} width="16" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Container15() {
  return (
    <div className="absolute content-stretch flex h-[44px] items-start justify-between left-[16px] top-[16px] w-[287.111px]" data-name="Container">
      <Container16 />
      <Icon4 />
    </div>
  );
}

function Text5() {
  return (
    <div className="bg-[#ececf0] h-[19.986px] relative rounded-[4px] shrink-0 w-[63.486px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start px-[8px] py-[2px] relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#0a0a0a] text-[12px] whitespace-nowrap">Low Risk</p>
      </div>
    </div>
  );
}

function Text6() {
  return (
    <div className="h-[15.986px] relative shrink-0 w-[87.361px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">high confidence</p>
      </div>
    </div>
  );
}

function Container19() {
  return (
    <div className="absolute content-stretch flex gap-[8px] h-[19.986px] items-center left-[16px] top-[68px] w-[287.111px]" data-name="Container">
      <Text5 />
      <Text6 />
    </div>
  );
}

function Button3() {
  return (
    <div className="bg-[#e9ebef] h-[104.875px] relative shrink-0 w-full" data-name="Button">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Container15 />
      <Container19 />
    </div>
  );
}

function Container22() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Grampians Livestock</p>
    </div>
  );
}

function Container23() {
  return (
    <div className="content-stretch flex h-[20px] items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Medium',sans-serif] font-medium leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Grampians, Victoria</p>
    </div>
  );
}

function Container21() {
  return (
    <div className="h-[44px] relative shrink-0 w-[263.111px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative size-full">
        <Container22 />
        <Container23 />
      </div>
    </div>
  );
}

function Icon5() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g clipPath="url(#clip0_4_1390)" id="Icon">
          <path d={svgPaths.p39ee6532} id="Vector" stroke="var(--stroke-0, #E17100)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8824 0.4431 0.0000)", strokeOpacity: "1" }} />
          <path d="M8 5.33333V8" id="Vector_2" stroke="var(--stroke-0, #E17100)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8824 0.4431 0.0000)", strokeOpacity: "1" }} />
          <path d="M8 10.6667H8.00667" id="Vector_3" stroke="var(--stroke-0, #E17100)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8824 0.4431 0.0000)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_4_1390">
            <rect fill="white" height="16" style={{ fill: "white", fillOpacity: "1" }} width="16" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Container20() {
  return (
    <div className="absolute content-stretch flex h-[44px] items-start justify-between left-[16px] top-[16px] w-[287.111px]" data-name="Container">
      <Container21 />
      <Icon5 />
    </div>
  );
}

function Text7() {
  return (
    <div className="bg-[#ececf0] h-[19.986px] relative rounded-[4px] shrink-0 w-[86.847px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start px-[8px] py-[2px] relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#0a0a0a] text-[12px] whitespace-nowrap">Medium Risk</p>
      </div>
    </div>
  );
}

function Text8() {
  return (
    <div className="h-[15.986px] relative shrink-0 w-[87.361px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">high confidence</p>
      </div>
    </div>
  );
}

function Container24() {
  return (
    <div className="absolute content-stretch flex gap-[8px] h-[19.986px] items-center left-[16px] top-[68px] w-[287.111px]" data-name="Container">
      <Text7 />
      <Text8 />
    </div>
  );
}

function Button4() {
  return (
    <div className="h-[104.875px] relative shrink-0 w-full" data-name="Button">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Container20 />
      <Container24 />
    </div>
  );
}

function Container27() {
  return (
    <div className="h-[24px] overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Alpine Horticulture</p>
    </div>
  );
}

function Container28() {
  return (
    <div className="content-stretch flex h-[20px] items-start overflow-clip relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Medium',sans-serif] font-medium leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Alpine Region, VIC</p>
    </div>
  );
}

function Container26() {
  return (
    <div className="h-[44px] relative shrink-0 w-[263.111px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative size-full">
        <Container27 />
        <Container28 />
      </div>
    </div>
  );
}

function Icon6() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g clipPath="url(#clip0_4_1390)" id="Icon">
          <path d={svgPaths.p39ee6532} id="Vector" stroke="var(--stroke-0, #E17100)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8824 0.4431 0.0000)", strokeOpacity: "1" }} />
          <path d="M8 5.33333V8" id="Vector_2" stroke="var(--stroke-0, #E17100)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8824 0.4431 0.0000)", strokeOpacity: "1" }} />
          <path d="M8 10.6667H8.00667" id="Vector_3" stroke="var(--stroke-0, #E17100)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.8824 0.4431 0.0000)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_4_1390">
            <rect fill="white" height="16" style={{ fill: "white", fillOpacity: "1" }} width="16" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Container25() {
  return (
    <div className="absolute content-stretch flex h-[44px] items-start justify-between left-[16px] top-[16px] w-[287.111px]" data-name="Container">
      <Container26 />
      <Icon6 />
    </div>
  );
}

function Text9() {
  return (
    <div className="bg-[#ececf0] h-[19.986px] relative rounded-[4px] shrink-0 w-[86.847px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start px-[8px] py-[2px] relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#0a0a0a] text-[12px] whitespace-nowrap">Medium Risk</p>
      </div>
    </div>
  );
}

function Text10() {
  return (
    <div className="h-[15.986px] relative shrink-0 w-[108.014px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">medium confidence</p>
      </div>
    </div>
  );
}

function Container29() {
  return (
    <div className="absolute content-stretch flex gap-[8px] h-[19.986px] items-center left-[16px] top-[68px] w-[287.111px]" data-name="Container">
      <Text9 />
      <Text10 />
    </div>
  );
}

function Button5() {
  return (
    <div className="h-[104.875px] relative shrink-0 w-full" data-name="Button">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Container25 />
      <Container29 />
    </div>
  );
}

function Container4() {
  return (
    <div className="absolute content-stretch flex flex-col h-[544.222px] items-start left-0 overflow-clip top-[86.89px] w-[319.111px]" data-name="Container">
      <Button1 />
      <Button2 />
      <Button3 />
      <Button4 />
      <Button5 />
    </div>
  );
}

function SupplierList() {
  return (
    <div className="absolute bg-white border-[rgba(0,0,0,0.1)] border-r-[0.889px] border-solid h-[631.111px] left-0 top-0 w-[320px]" data-name="SupplierList">
      <Container3 />
      <Container4 />
    </div>
  );
}

function Heading2() {
  return (
    <div className="h-[30px] relative shrink-0 w-full" data-name="Heading 2">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[30px] left-0 not-italic text-[#0a0a0a] text-[20px] top-[-2.11px] whitespace-nowrap">Risk Profile</p>
    </div>
  );
}

function Paragraph1() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Murray Valley Produce</p>
    </div>
  );
}

function Container30() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[86.889px] items-start left-0 pb-[0.889px] pt-[16px] px-[16px] top-0 w-[383.111px]" data-name="Container">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Heading2 />
      <Paragraph1 />
    </div>
  );
}

function Icon7() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p37f49070} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Text11() {
  return (
    <div className="h-[20px] relative shrink-0 w-[122.722px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] whitespace-nowrap">Overall Assessment</p>
      </div>
    </div>
  );
}

function Container33() {
  return (
    <div className="content-stretch flex gap-[8px] h-[20px] items-center relative shrink-0 w-full" data-name="Container">
      <Icon7 />
      <Text11 />
    </div>
  );
}

function Paragraph2() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Low risk: minimal overlap with protected areas</p>
    </div>
  );
}

function Container34() {
  return (
    <div className="content-stretch flex h-[15.986px] items-start relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[16px] min-h-px min-w-px not-italic relative text-[#717182] text-[12px]">Location confidence: high</p>
    </div>
  );
}

function Container32() {
  return (
    <div className="bg-[#ececf0] h-[95.986px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div className="content-stretch flex flex-col gap-[8px] items-start pt-[12px] px-[12px] relative size-full">
        <Container33 />
        <Paragraph2 />
        <Container34 />
      </div>
    </div>
  );
}

function Icon8() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g clipPath="url(#clip0_4_1368)" id="Icon">
          <path d={svgPaths.pe3c3980} id="Vector" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d={svgPaths.p38f09280} id="Vector_2" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d={svgPaths.p2c490180} id="Vector_3" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_4_1368">
            <rect fill="white" height="16" style={{ fill: "white", fillOpacity: "1" }} width="16" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Heading3() {
  return (
    <div className="h-[27px] relative shrink-0 w-[203.708px]" data-name="Heading 3">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[27px] left-0 not-italic text-[#0a0a0a] text-[18px] top-[-1.11px] whitespace-nowrap">Protected Areas (CAPAD)</p>
      </div>
    </div>
  );
}

function Container36() {
  return (
    <div className="content-stretch flex gap-[8px] h-[27px] items-center relative shrink-0 w-full" data-name="Container">
      <Icon8 />
      <Heading3 />
    </div>
  );
}

function Text12() {
  return (
    <div className="h-[20px] relative shrink-0 w-[121.597px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">Overlap percentage</p>
      </div>
    </div>
  );
}

function Text13() {
  return (
    <div className="h-[20px] relative shrink-0 w-[19.556px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] whitespace-nowrap">0%</p>
      </div>
    </div>
  );
}

function Container37() {
  return (
    <div className="h-[20px] relative shrink-0 w-full" data-name="Container">
      <div className="content-stretch flex items-start justify-between relative size-full">
        <Text12 />
        <Text13 />
      </div>
    </div>
  );
}

function Container35() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] h-[55px] items-start relative shrink-0 w-full" data-name="Container">
      <Container36 />
      <Container37 />
    </div>
  );
}

function Icon9() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p17bbd280} id="Vector" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d="M8 14.6667V12.6667" id="Vector_2" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Heading4() {
  return (
    <div className="h-[27px] relative shrink-0 w-[180.028px]" data-name="Heading 3">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[27px] left-0 not-italic text-[#0a0a0a] text-[18px] top-[-1.11px] whitespace-nowrap">Key Biodiversity Areas</p>
      </div>
    </div>
  );
}

function Container39() {
  return (
    <div className="content-stretch flex gap-[8px] h-[27px] items-center relative shrink-0 w-full" data-name="Container">
      <Icon9 />
      <Heading4 />
    </div>
  );
}

function Container40() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Not within KBA</p>
    </div>
  );
}

function Container38() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] h-[55px] items-start relative shrink-0 w-full" data-name="Container">
      <Container39 />
      <Container40 />
    </div>
  );
}

function Icon10() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p19bc7f80} id="Vector" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d="M8 6V8.66667" id="Vector_2" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d="M8 11.3333H8.00667" id="Vector_3" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Heading5() {
  return (
    <div className="flex-[1_0_0] h-[27px] min-h-px min-w-px relative" data-name="Heading 3">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[27px] left-0 not-italic text-[#0a0a0a] text-[18px] top-[-1.11px] whitespace-nowrap">Threatened Species (EPBC)</p>
      </div>
    </div>
  );
}

function Container43() {
  return (
    <div className="h-[27px] relative shrink-0 w-[241.181px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center relative size-full">
        <Icon10 />
        <Heading5 />
      </div>
    </div>
  );
}

function Icon11() {
  return (
    <div className="absolute left-[53.14px] size-[12px] top-[4px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d="M4.5 9L7.5 6L4.5 3" id="Vector" stroke="var(--stroke-0, #030213)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.0118 0.0078 0.0745)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button6() {
  return (
    <div className="h-[20px] relative shrink-0 w-[65.139px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[20px] left-[25px] not-italic text-[#030213] text-[14px] text-center top-[-1px] whitespace-nowrap">View all</p>
        <Icon11 />
      </div>
    </div>
  );
}

function Container42() {
  return (
    <div className="content-stretch flex h-[27px] items-center justify-between relative shrink-0 w-full" data-name="Container">
      <Container43 />
      <Button6 />
    </div>
  );
}

function Text14() {
  return (
    <div className="h-[20px] relative shrink-0 w-[125.389px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">Species within 10km</p>
      </div>
    </div>
  );
}

function Text15() {
  return (
    <div className="h-[20px] relative shrink-0 w-[7.778px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] whitespace-nowrap">2</p>
      </div>
    </div>
  );
}

function Container44() {
  return (
    <div className="content-stretch flex h-[20px] items-start justify-between relative shrink-0 w-full" data-name="Container">
      <Text14 />
      <Text15 />
    </div>
  );
}

function Container41() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] h-[55px] items-start relative shrink-0 w-full" data-name="Container">
      <Container42 />
      <Container44 />
    </div>
  );
}

function Icon12() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p17bbd280} id="Vector" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d="M8 14.6667V12.6667" id="Vector_2" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Heading6() {
  return (
    <div className="h-[27px] relative shrink-0 w-[231.417px]" data-name="Heading 3">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[27px] left-0 not-italic text-[#0a0a0a] text-[18px] top-[-1.11px] whitespace-nowrap">Vegetation Condition (NVIS)</p>
      </div>
    </div>
  );
}

function Container46() {
  return (
    <div className="content-stretch flex gap-[8px] h-[27px] items-center relative shrink-0 w-full" data-name="Container">
      <Icon12 />
      <Heading6 />
    </div>
  );
}

function Text16() {
  return (
    <div className="h-[20px] relative shrink-0 w-[100.333px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">Condition grade</p>
      </div>
    </div>
  );
}

function Text17() {
  return (
    <div className="h-[20px] relative shrink-0 w-[57.75px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] whitespace-nowrap">Modified</p>
      </div>
    </div>
  );
}

function Container48() {
  return (
    <div className="h-[20px] relative shrink-0 w-full" data-name="Container">
      <div className="content-stretch flex items-start justify-between relative size-full">
        <Text16 />
        <Text17 />
      </div>
    </div>
  );
}

function Text18() {
  return (
    <div className="h-[20px] relative shrink-0 w-[113.236px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">Corridor proximity</p>
      </div>
    </div>
  );
}

function Text19() {
  return (
    <div className="h-[20px] relative shrink-0 w-[35.722px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] whitespace-nowrap">250m</p>
      </div>
    </div>
  );
}

function Container49() {
  return (
    <div className="content-stretch flex h-[20px] items-start justify-between relative shrink-0 w-full" data-name="Container">
      <Text18 />
      <Text19 />
    </div>
  );
}

function Container47() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] h-[44px] items-start relative shrink-0 w-full" data-name="Container">
      <Container48 />
      <Container49 />
    </div>
  );
}

function Container45() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] h-[79px] items-start relative shrink-0 w-full" data-name="Container">
      <Container46 />
      <Container47 />
    </div>
  );
}

function Paragraph3() {
  return (
    <div className="content-stretch flex h-[15.986px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[16px] min-h-px min-w-px not-italic relative text-[#717182] text-[12px]">Data as of: March 2026</p>
    </div>
  );
}

function Paragraph4() {
  return (
    <div className="content-stretch flex h-[15.986px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">Sources: CAPAD 2024, ALA (2016-2026), EPBC SPRAT, NVIS v6.0</p>
    </div>
  );
}

function Container51() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] h-[35.972px] items-start relative shrink-0 w-full" data-name="Container">
      <Paragraph3 />
      <Paragraph4 />
    </div>
  );
}

function Container50() {
  return (
    <div className="content-stretch flex flex-col h-[52.861px] items-start pt-[16.889px] relative shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-solid border-t-[0.889px] inset-0 pointer-events-none" />
      <Container51 />
    </div>
  );
}

function Container31() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[16px] h-[504.847px] items-start left-0 pt-[16px] px-[16px] top-[86.89px] w-[383.111px]" data-name="Container">
      <Container32 />
      <Container35 />
      <Container38 />
      <Container41 />
      <Container45 />
      <Container50 />
    </div>
  );
}

function RiskProfile() {
  return (
    <div className="absolute bg-white border-[rgba(0,0,0,0.1)] border-l-[0.889px] border-solid h-[631.111px] left-[983.11px] overflow-clip top-0 w-[384px]" data-name="RiskProfile">
      <Container30 />
      <Container31 />
    </div>
  );
}

function Icon13() {
  return (
    <div className="absolute left-[73.71px] size-[48px] top-0" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 48 48">
        <g id="Icon">
          <path d={svgPaths.p30cd2b80} id="Vector" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
          <path d={svgPaths.pd151bb0} id="Vector_2" stroke="var(--stroke-0, #717182)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" style={{ stroke: "color(display-p3 0.4431 0.4431 0.5098)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Paragraph5() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-0 top-[60px] w-[195.417px]" data-name="Paragraph">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] text-center whitespace-nowrap">Showing Murray Valley Produce</p>
    </div>
  );
}

function Paragraph6() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-0 top-[84px] w-[195.417px]" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[16px] min-h-px min-w-px not-italic relative text-[#717182] text-[12px] text-center">GIS overlay visualization</p>
    </div>
  );
}

function Container53() {
  return (
    <div className="h-[99.986px] relative shrink-0 w-[195.417px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <Icon13 />
        <Paragraph5 />
        <Paragraph6 />
      </div>
    </div>
  );
}

function Container52() {
  return (
    <div className="absolute content-stretch flex h-[631.111px] items-center justify-center left-0 px-[233.847px] top-0 w-[663.111px]" data-name="Container">
      <Container53 />
    </div>
  );
}

function Icon14() {
  return (
    <div className="h-[16px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <div className="absolute inset-[12.5%_12.5%_62.5%_62.5%]" data-name="Vector">
        <div className="absolute inset-[-16.67%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.33333 5.33333">
            <path d={svgPaths.p1efb2580} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[62.5%_62.5%_12.5%_12.5%]" data-name="Vector">
        <div className="absolute inset-[-16.67%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 5.33333 5.33333">
            <path d={svgPaths.p39dbf080} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[12.5%_12.5%_58.33%_58.33%]" data-name="Vector">
        <div className="absolute inset-[-14.29%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6 6">
            <path d={svgPaths.p19399880} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[58.33%_58.33%_12.5%_12.5%]" data-name="Vector">
        <div className="absolute inset-[-14.29%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 6 6">
            <path d={svgPaths.p3822980} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Button7() {
  return (
    <div className="absolute bg-white content-stretch flex flex-col items-start left-[613.33px] pb-[0.889px] pt-[8.889px] px-[8.889px] rounded-[10px] size-[33.778px] top-[16px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <Icon14 />
    </div>
  );
}

function Container55() {
  return (
    <div className="content-stretch flex h-[15.986px] items-start relative shrink-0 w-full" data-name="Container">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[16px] min-h-px min-w-px not-italic relative text-[#717182] text-[12px]">Viewing</p>
    </div>
  );
}

function Container56() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Container">
      <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#0a0a0a] text-[14px] whitespace-nowrap">Murray Valley Produce</p>
    </div>
  );
}

function Container54() {
  return (
    <div className="absolute bg-white content-stretch flex flex-col gap-[4px] h-[65.764px] items-start left-[16px] pb-[0.889px] pt-[12.889px] px-[12.889px] rounded-[10px] top-[549.35px] w-[168.736px]" data-name="Container">
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px] shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]" />
      <Container55 />
      <Container56 />
    </div>
  );
}

function MapView() {
  return (
    <div className="absolute bg-[rgba(236,236,240,0.3)] h-[631.111px] left-[320px] top-0 w-[663.111px]" data-name="MapView">
      <Container52 />
      <Button7 />
      <Container54 />
    </div>
  );
}

function Container2() {
  return (
    <div className="flex-[631.111_0_0] min-h-px min-w-px relative w-[1367.111px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid overflow-clip relative rounded-[inherit] size-full">
        <SupplierList />
        <RiskProfile />
        <MapView />
      </div>
    </div>
  );
}

export default function TestingFunctionalityMain() {
  return (
    <div className="bg-white content-stretch flex flex-col items-start relative size-full" data-name="Testing Functionality_Main3">
      <Header />
      <Container2 />
    </div>
  );
}