import svgPaths from "./svg-jcor124uuv";

function Heading() {
  return (
    <div className="h-[30px] relative shrink-0 w-full" data-name="Heading 2">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[30px] left-0 not-italic text-[#0a0a0a] text-[20px] top-[-2.11px] whitespace-nowrap">Configure GIS Layers</p>
    </div>
  );
}

function Paragraph() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">Select layers for biodiversity risk screening</p>
    </div>
  );
}

function Container2() {
  return (
    <div className="h-[54px] relative shrink-0 w-[260.486px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col gap-[4px] items-start relative size-full">
        <Heading />
        <Paragraph />
      </div>
    </div>
  );
}

function Icon() {
  return (
    <div className="h-[16px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <div className="absolute inset-1/4" data-name="Vector">
        <div className="absolute inset-[-8.33%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.33333 9.33333">
            <path d={svgPaths.p48af40} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute inset-1/4" data-name="Vector">
        <div className="absolute inset-[-8.33%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 9.33333 9.33333">
            <path d={svgPaths.p30908200} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Button() {
  return (
    <div className="relative rounded-[10px] shrink-0 size-[32px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start pt-[8px] px-[8px] relative size-full">
        <Icon />
      </div>
    </div>
  );
}

function Container1() {
  return (
    <div className="h-[87px] relative shrink-0 w-[820px]" data-name="Container">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-center justify-between pb-[16.889px] pt-[16px] px-[16px] relative size-full">
        <Container2 />
        <Button />
      </div>
    </div>
  );
}

function Icon1() {
  return (
    <div className="relative shrink-0 size-[12px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d="M10 3L4.5 8.5L2 6" id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "white", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button1() {
  return (
    <div className="absolute bg-[#030213] content-stretch flex items-center justify-center left-0 px-[4px] py-[1.778px] rounded-[4px] size-[20px] top-[2px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[#030213] border-[1.778px] border-solid inset-0 pointer-events-none rounded-[4px]" />
      <Icon1 />
    </div>
  );
}

function Heading1() {
  return (
    <div className="absolute h-[24px] left-0 top-0 w-[170.458px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">CAPAD Protected Areas</p>
    </div>
  );
}

function Text() {
  return (
    <div className="absolute bg-[#fef3c6] content-stretch flex h-[19.986px] items-start left-[205.22px] px-[8px] py-[2px] rounded-[4px] top-[4.22px] w-[63.389px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#973c00] text-[12px] whitespace-nowrap">Required</p>
    </div>
  );
}

function Text1() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[285.22px] top-[4.22px] w-[90.917px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">Updated biennial</p>
    </div>
  );
}

function Container8() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading1 />
      <Text />
      <Text1 />
    </div>
  );
}

function Paragraph1() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Australian protected areas database showing gazetted reserves, national parks, and conservation areas</p>
    </div>
  );
}

function Container7() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container8 />
      <Paragraph1 />
    </div>
  );
}

function Container6() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button1 />
      <Container7 />
    </div>
  );
}

function Container5() {
  return (
    <div className="bg-[rgba(3,2,19,0.05)] h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[#030213] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container6 />
      </div>
    </div>
  );
}

function Icon2() {
  return (
    <div className="relative shrink-0 size-[12px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d="M10 3L4.5 8.5L2 6" id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "white", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button2() {
  return (
    <div className="absolute bg-[#030213] content-stretch flex items-center justify-center left-0 px-[4px] py-[1.778px] rounded-[4px] size-[20px] top-[2px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[#030213] border-[1.778px] border-solid inset-0 pointer-events-none rounded-[4px]" />
      <Icon2 />
    </div>
  );
}

function Heading2() {
  return (
    <div className="absolute h-[24px] left-0 top-0 w-[160.028px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Key Biodiversity Areas</p>
    </div>
  );
}

function Text2() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[184.22px] top-[1.44px] w-[84.667px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">Updated annual</p>
    </div>
  );
}

function Container12() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading2 />
      <Text2 />
    </div>
  );
}

function Paragraph2() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Globally significant sites for biodiversity conservation identified by BirdLife International</p>
    </div>
  );
}

function Container11() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container12 />
      <Paragraph2 />
    </div>
  );
}

function Container10() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button2 />
      <Container11 />
    </div>
  );
}

function Container9() {
  return (
    <div className="bg-[rgba(3,2,19,0.05)] h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[#030213] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container10 />
      </div>
    </div>
  );
}

function Icon3() {
  return (
    <div className="relative shrink-0 size-[12px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d="M10 3L4.5 8.5L2 6" id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "white", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button3() {
  return (
    <div className="absolute bg-[#030213] content-stretch flex items-center justify-center left-0 px-[4px] py-[1.778px] rounded-[4px] size-[20px] top-[2px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[#030213] border-[1.778px] border-solid inset-0 pointer-events-none rounded-[4px]" />
      <Icon3 />
    </div>
  );
}

function Heading3() {
  return (
    <div className="absolute h-[24px] left-0 top-0 w-[233.292px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">EPBC SPRAT Threatened Species</p>
    </div>
  );
}

function Text3() {
  return (
    <div className="absolute bg-[#fef3c6] content-stretch flex h-[19.986px] items-start left-[266.22px] px-[8px] py-[2px] rounded-[4px] top-[1.67px] w-[63.389px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#973c00] text-[12px] whitespace-nowrap">Required</p>
    </div>
  );
}

function Text4() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[340.22px] top-[5.67px] w-[96.542px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">Updated quarterly</p>
    </div>
  );
}

function Container16() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading3 />
      <Text3 />
      <Text4 />
    </div>
  );
}

function Paragraph3() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Species and communities listed under the Environment Protection and Biodiversity Conservation Act</p>
    </div>
  );
}

function Container15() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container16 />
      <Paragraph3 />
    </div>
  );
}

function Container14() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button3 />
      <Container15 />
    </div>
  );
}

function Container13() {
  return (
    <div className="bg-[rgba(3,2,19,0.05)] h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[#030213] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container14 />
      </div>
    </div>
  );
}

function Icon4() {
  return (
    <div className="relative shrink-0 size-[12px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d="M10 3L4.5 8.5L2 6" id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "white", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button4() {
  return (
    <div className="absolute bg-[#030213] content-stretch flex items-center justify-center left-0 px-[4px] py-[1.778px] rounded-[4px] size-[20px] top-[2px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[#030213] border-[1.778px] border-solid inset-0 pointer-events-none rounded-[4px]" />
      <Icon4 />
    </div>
  );
}

function Heading4() {
  return (
    <div className="absolute h-[24px] left-[0.22px] top-[-0.11px] w-[284px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">NVIS Vegetation Condition</p>
    </div>
  );
}

function Text5() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[230.22px] top-[1.89px] w-[91.514px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] w-[203px]">Updated 5-yearly</p>
    </div>
  );
}

function Container20() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading4 />
      <Text5 />
    </div>
  );
}

function Paragraph4() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">National Vegetation Information System showing vegetation types, extent, and condition</p>
    </div>
  );
}

function Container19() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container20 />
      <Paragraph4 />
    </div>
  );
}

function Container18() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button4 />
      <Container19 />
    </div>
  );
}

function Container17() {
  return (
    <div className="bg-[rgba(3,2,19,0.05)] h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[#030213] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container18 />
      </div>
    </div>
  );
}

function Button5() {
  return <div className="absolute bg-white border-[1.778px] border-[rgba(0,0,0,0)] border-solid left-0 rounded-[4px] size-[20px] top-[2px]" data-name="Button" />;
}

function Heading5() {
  return (
    <div className="absolute h-[24px] left-[0.22px] top-[0.11px] w-[272px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Aqueduct Water Risk</p>
    </div>
  );
}

function Text6() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[179.22px] top-[3.11px] w-[84.667px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] w-[168px]">Updated annual</p>
    </div>
  );
}

function Container24() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading5 />
      <Text6 />
    </div>
  );
}

function Paragraph5() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Global water risk indicators including baseline water stress and flood occurrence</p>
    </div>
  );
}

function Container23() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container24 />
      <Paragraph5 />
    </div>
  );
}

function Container22() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button5 />
      <Container23 />
    </div>
  );
}

function Container21() {
  return (
    <div className="bg-white h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container22 />
      </div>
    </div>
  );
}

function Button6() {
  return <div className="absolute bg-white border-[1.778px] border-[rgba(0,0,0,0)] border-solid left-0 rounded-[4px] size-[20px] top-[2px]" data-name="Button" />;
}

function Heading6() {
  return (
    <div className="absolute h-[24px] left-[0.22px] top-[0.33px] w-[243px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">Global Forest Cover</p>
    </div>
  );
}

function Text7() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[164.22px] top-[3.33px] w-[92.903px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">Updated monthly</p>
    </div>
  );
}

function Container28() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading6 />
      <Text7 />
    </div>
  );
}

function Paragraph6() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Tree cover extent and deforestation alerts from Global Forest Watch</p>
    </div>
  );
}

function Container27() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container28 />
      <Paragraph6 />
    </div>
  );
}

function Container26() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button6 />
      <Container27 />
    </div>
  );
}

function Container25() {
  return (
    <div className="bg-white h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container26 />
      </div>
    </div>
  );
}

function Icon5() {
  return (
    <div className="relative shrink-0 size-[12px]" data-name="Icon">
      <svg className="absolute block inset-0 size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d="M10 3L4.5 8.5L2 6" id="Vector" stroke="var(--stroke-0, white)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "white", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button7() {
  return (
    <div className="absolute bg-[#030213] content-stretch flex items-center justify-center left-0 px-[4px] py-[1.778px] rounded-[4px] size-[20px] top-[2px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[#030213] border-[1.778px] border-solid inset-0 pointer-events-none rounded-[4px]" />
      <Icon5 />
    </div>
  );
}

function Heading7() {
  return (
    <div className="absolute h-[24px] left-[0.22px] top-[-0.44px] w-[171px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">VLUIS Land Use (Victoria)</p>
    </div>
  );
}

function Text8() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[210.22px] top-[1.56px] w-[84.667px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] w-[119px]">Updated annual</p>
    </div>
  );
}

function Container32() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading7 />
      <Text8 />
    </div>
  );
}

function Paragraph7() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">Victorian Land Use Information System showing parcel-level land use classifications</p>
    </div>
  );
}

function Container31() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container32 />
      <Paragraph7 />
    </div>
  );
}

function Container30() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button7 />
      <Container31 />
    </div>
  );
}

function Container29() {
  return (
    <div className="bg-[rgba(3,2,19,0.05)] h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[#030213] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container30 />
      </div>
    </div>
  );
}

function Button8() {
  return <div className="absolute bg-white border-[1.778px] border-[rgba(0,0,0,0)] border-solid left-0 rounded-[4px] size-[20px] top-[2px]" data-name="Button" />;
}

function Heading8() {
  return (
    <div className="absolute h-[24px] left-0 top-0 w-[261.181px]" data-name="Heading 4">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-0 not-italic text-[#0a0a0a] text-[16px] top-[-2.11px] whitespace-nowrap">CLUM/ACLUMP Land Use (National)</p>
    </div>
  );
}

function Text9() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[286.22px] top-[1.78px] w-[91.514px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[16px] not-italic relative shrink-0 text-[#717182] text-[12px] whitespace-nowrap">Updated 5-yearly</p>
    </div>
  );
}

function Container36() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Container">
      <Heading8 />
      <Text9 />
    </div>
  );
}

function Paragraph8() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#717182] text-[14px]">National land use mapping showing agricultural and other land uses at 50m resolution</p>
    </div>
  );
}

function Container35() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[32px] top-0 w-[776px]" data-name="Container">
      <Container36 />
      <Paragraph8 />
    </div>
  );
}

function Container34() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Container">
      <Button8 />
      <Container35 />
    </div>
  );
}

function Container33() {
  return (
    <div className="bg-white h-[81.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col items-start pb-[0.889px] pt-[16.889px] px-[16.889px] relative size-full">
        <Container34 />
      </div>
    </div>
  );
}

function Container4() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] h-[738px] items-start relative shrink-0 w-[771px]" data-name="Container">
      <Container5 />
      <Container9 />
      <Container13 />
      <Container17 />
      <Container21 />
      <Container25 />
      <Container29 />
      <Container33 />
    </div>
  );
}

function Container3() {
  return (
    <div className="h-[672px] relative shrink-0 w-[802px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start overflow-clip pl-[16px] pr-[36.444px] pt-[16px] relative rounded-[inherit] size-full">
        <Container4 />
      </div>
    </div>
  );
}

function Label() {
  return (
    <div className="absolute content-stretch flex h-[18.667px] items-start left-0 top-[2.67px] w-[185.306px]" data-name="Label">
      <p className="font-['Inter:Medium',sans-serif] font-medium leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">Save configuration (optional)</p>
    </div>
  );
}

function TextInput() {
  return (
    <div className="absolute bg-white h-[42px] left-[0.11px] rounded-[10px] top-[28.22px] w-[774px]" data-name="Text Input">
      <div className="content-stretch flex items-center overflow-clip px-[12px] py-[8px] relative rounded-[inherit] size-full">
        <p className="font-['Inter:Regular',sans-serif] font-normal leading-[normal] not-italic relative shrink-0 text-[16px] text-[rgba(10,10,10,0.5)] whitespace-nowrap">e.g., Victoria Dairy Screening</p>
      </div>
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px]" />
    </div>
  );
}

function Container38() {
  return (
    <div className="h-[70px] relative shrink-0 w-[804px]" data-name="Container">
      <Label />
      <TextInput />
    </div>
  );
}

function Container40() {
  return (
    <div className="h-[20px] relative shrink-0 w-[129.236px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#717182] text-[14px] whitespace-nowrap">5 of 8 layers selected</p>
      </div>
    </div>
  );
}

function Button9() {
  return (
    <div className="h-[40px] relative rounded-[10px] shrink-0 w-[79.833px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-[40.5px] not-italic text-[#0a0a0a] text-[16px] text-center top-[5.89px] whitespace-nowrap">Cancel</p>
      </div>
    </div>
  );
}

function Button10() {
  return (
    <div className="bg-[#030213] h-[40px] relative rounded-[10px] shrink-0 w-[179.361px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-[90.5px] not-italic text-[16px] text-center text-white top-[5.89px] whitespace-nowrap">Apply Configuration</p>
      </div>
    </div>
  );
}

function Container41() {
  return (
    <div className="h-[40px] relative shrink-0 w-[267.194px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center relative size-full">
        <Button9 />
        <Button10 />
      </div>
    </div>
  );
}

function Container39() {
  return (
    <div className="content-stretch flex h-[40px] items-center justify-between relative shrink-0 w-full" data-name="Container">
      <Container40 />
      <Container41 />
    </div>
  );
}

function Container37() {
  return (
    <div className="h-[155px] relative shrink-0 w-[810px]" data-name="Container">
      <div aria-hidden="true" className="absolute border-[rgba(0,0,0,0.1)] border-solid border-t-[0.889px] inset-0 pointer-events-none" />
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col gap-[12px] items-start pt-[16.889px] px-[16px] relative size-full">
        <Container38 />
        <Container39 />
      </div>
    </div>
  );
}

export default function Container() {
  return (
    <div className="bg-white content-stretch flex flex-col items-start p-[0.889px] relative rounded-[10px] size-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[0.889px] border-[rgba(0,0,0,0.1)] border-solid inset-0 pointer-events-none rounded-[10px] shadow-[0px_10px_15px_0px_rgba(0,0,0,0.1),0px_4px_6px_0px_rgba(0,0,0,0.1)]" />
      <Container1 />
      <Container3 />
      <Container37 />
    </div>
  );
}