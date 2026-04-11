import svgPaths from "./svg-crl28c1h5o";

function Heading() {
  return (
    <div className="h-[32px] relative shrink-0 w-full" data-name="Heading 1">
      <p className="absolute font-['Inter:Bold',sans-serif] font-bold leading-[32px] left-0 not-italic text-[#0f172b] text-[24px] top-[-1px] whitespace-nowrap">{`Upload & Extract`}</p>
    </div>
  );
}

function Paragraph() {
  return (
    <div className="h-[20px] relative shrink-0 w-full" data-name="Paragraph">
      <p className="absolute font-['Inter:Regular',sans-serif] font-normal leading-[20px] left-0 not-italic text-[#62748e] text-[14px] top-[0.5px] whitespace-nowrap">Upload supplier documents to extract key information using OCR. You can edit extracted fields before continuing.</p>
    </div>
  );
}

function Container1() {
  return (
    <div className="content-stretch flex flex-col gap-[4px] h-[56px] items-start relative shrink-0 w-full" data-name="Container">
      <Heading />
      <Paragraph />
    </div>
  );
}

function Icon() {
  return (
    <div className="relative shrink-0 size-[28px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 28 28">
        <g id="Icon">
          <path d={svgPaths.p2ba01680} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d={svgPaths.p1264cb00} id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d="M14 3.5V17.5" id="Vector_3" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Container4() {
  return (
    <div className="absolute bg-[#f1f5f9] content-stretch flex items-center justify-center left-[359.5px] px-[18px] rounded-[16px] size-[64px] top-0" data-name="Container">
      <Icon />
    </div>
  );
}

function Paragraph1() {
  return (
    <div className="h-[24px] relative shrink-0 w-full" data-name="Paragraph">
      <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-[155px] not-italic text-[#314158] text-[16px] text-center top-[-1px] whitespace-nowrap">{`Drag & drop files here, or click to browse`}</p>
    </div>
  );
}

function Paragraph2() {
  return (
    <div className="h-[20px] relative shrink-0 w-full" data-name="Paragraph">
      <p className="-translate-x-1/2 absolute font-['Inter:Regular',sans-serif] font-normal leading-[20px] left-[155.86px] not-italic text-[#90a1b9] text-[14px] text-center top-[0.5px] whitespace-nowrap">PDF, PNG, JPG, or CSV files up to 10MB</p>
    </div>
  );
}

function Container5() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[4px] h-[48px] items-start left-[236.27px] top-[80px] w-[310.469px]" data-name="Container">
      <Paragraph1 />
      <Paragraph2 />
    </div>
  );
}

function Text() {
  return (
    <div className="bg-[#f1f5f9] h-[19px] relative rounded-[4px] shrink-0 w-[35.555px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Semi_Bold',sans-serif] font-semibold leading-[15px] left-[18px] not-italic text-[#62748e] text-[10px] text-center top-[2.5px] whitespace-nowrap">PDF</p>
      </div>
    </div>
  );
}

function Text1() {
  return (
    <div className="bg-[#f1f5f9] flex-[1_0_0] h-[19px] min-h-px min-w-px relative rounded-[4px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Semi_Bold',sans-serif] font-semibold leading-[15px] left-[19px] not-italic text-[#62748e] text-[10px] text-center top-[2.5px] whitespace-nowrap">PNG</p>
      </div>
    </div>
  );
}

function Text2() {
  return (
    <div className="bg-[#f1f5f9] h-[19px] relative rounded-[4px] shrink-0 w-[35.742px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Semi_Bold',sans-serif] font-semibold leading-[15px] left-[18px] not-italic text-[#62748e] text-[10px] text-center top-[2.5px] whitespace-nowrap">JPG</p>
      </div>
    </div>
  );
}

function Text3() {
  return (
    <div className="bg-[#f1f5f9] h-[19px] relative rounded-[4px] shrink-0 w-[37.148px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Semi_Bold',sans-serif] font-semibold leading-[15px] left-[19px] not-italic text-[#62748e] text-[10px] text-center top-[2.5px] whitespace-nowrap">CSV</p>
      </div>
    </div>
  );
}

function Container6() {
  return (
    <div className="absolute content-stretch flex gap-[8px] h-[19px] items-center left-[306.51px] top-[148px] w-[169.984px]" data-name="Container">
      <Text />
      <Text1 />
      <Text2 />
      <Text3 />
    </div>
  );
}

function Container3() {
  return (
    <div className="h-[167px] relative shrink-0 w-full" data-name="Container">
      <Container4 />
      <Container5 />
      <Container6 />
    </div>
  );
}

function Container2() {
  return (
    <div className="bg-white h-[251px] relative rounded-[16px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-2 border-[#e2e8f0] border-dashed inset-0 pointer-events-none rounded-[16px]" />
      <div className="content-stretch flex flex-col items-start pb-[2px] pt-[42px] px-[42px] relative size-full">
        <Container3 />
      </div>
    </div>
  );
}

function UploadExtractPage() {
  return (
    <div className="h-[331px] relative shrink-0 w-[867px]" data-name="UploadExtractPage">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col gap-[24px] items-start relative size-full">
        <Container1 />
        <Container2 />
      </div>
    </div>
  );
}

function Container() {
  return (
    <div className="flex-[899_0_0] h-[772px] min-h-px min-w-px relative" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start pl-[16px] pt-[72px] relative size-full">
        <UploadExtractPage />
      </div>
    </div>
  );
}

function Layout() {
  return (
    <div className="absolute bg-[#f8fafc] content-stretch flex h-[772px] items-start left-0 top-0 w-[899px]" data-name="Layout">
      <Container />
    </div>
  );
}

function Icon1() {
  return (
    <div className="h-[20px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <div className="absolute bottom-1/2 left-[16.67%] right-[16.67%] top-1/2" data-name="Vector">
        <div className="absolute inset-[-0.83px_-6.25%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15 1.66667">
            <path d="M0.833333 0.833333H14.1667" id="Vector" stroke="var(--stroke-0, #62748E)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" style={{ stroke: "color(display-p3 0.3843 0.4549 0.5569)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute bottom-3/4 left-[16.67%] right-[16.67%] top-1/4" data-name="Vector">
        <div className="absolute inset-[-0.83px_-6.25%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15 1.66667">
            <path d="M0.833333 0.833333H14.1667" id="Vector" stroke="var(--stroke-0, #62748E)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" style={{ stroke: "color(display-p3 0.3843 0.4549 0.5569)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute bottom-1/4 left-[16.67%] right-[16.67%] top-3/4" data-name="Vector">
        <div className="absolute inset-[-0.83px_-6.25%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15 1.66667">
            <path d="M0.833333 0.833333H14.1667" id="Vector" stroke="var(--stroke-0, #62748E)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" style={{ stroke: "color(display-p3 0.3843 0.4549 0.5569)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Button() {
  return (
    <div className="absolute content-stretch flex flex-col items-start left-[16px] size-[20px] top-[17.5px]" data-name="Button">
      <Icon1 />
    </div>
  );
}

function Text4() {
  return (
    <div className="h-[20px] relative shrink-0 w-[98.633px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Regular',sans-serif] font-normal leading-[20px] left-0 not-italic text-[#90a1b9] text-[14px] top-[0.5px] whitespace-nowrap">Supplier Intake</p>
      </div>
    </div>
  );
}

function Icon2() {
  return (
    <div className="relative shrink-0 size-[14px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 14 14">
        <g id="Icon">
          <path d="M5.25 10.5L8.75 7L5.25 3.5" id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.16667" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Text5() {
  return (
    <div className="flex-[1_0_0] h-[20px] min-h-px min-w-px relative" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[20px] left-0 not-italic text-[#314158] text-[14px] top-[0.5px] whitespace-nowrap">{`Upload & Extract`}</p>
      </div>
    </div>
  );
}

function Container7() {
  return (
    <div className="absolute content-stretch flex gap-[6px] h-[20px] items-center left-[52px] top-[17.5px] w-[236.391px]" data-name="Container">
      <Text4 />
      <Icon2 />
      <Text5 />
    </div>
  );
}

function Icon3() {
  return (
    <div className="absolute left-[12px] size-[12px] top-[8px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d={svgPaths.p2752e200} id="Vector" stroke="var(--stroke-0, #007A55)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.0000 0.4784 0.3333)", strokeOpacity: "1" }} />
          <path d="M8.5 4L6 1.5L3.5 4" id="Vector_2" stroke="var(--stroke-0, #007A55)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.0000 0.4784 0.3333)", strokeOpacity: "1" }} />
          <path d="M6 1.5V7.5" id="Vector_3" stroke="var(--stroke-0, #007A55)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.0000 0.4784 0.3333)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button1() {
  return (
    <div className="bg-white h-[28px] relative rounded-[8px] shadow-[0px_1px_3px_0px_rgba(0,0,0,0.1),0px_1px_2px_0px_rgba(0,0,0,0.1)] shrink-0 w-[83.266px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <Icon3 />
        <p className="-translate-x-1/2 absolute font-['Inter:Semi_Bold',sans-serif] font-semibold leading-[16px] left-[51px] not-italic text-[#007a55] text-[12px] text-center top-[6.5px] whitespace-nowrap">Upload</p>
      </div>
    </div>
  );
}

function Icon4() {
  return (
    <div className="absolute left-[12px] size-[12px] top-[8px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d={svgPaths.pb47e900} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d={svgPaths.p289e9716} id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d={svgPaths.p39602200} id="Vector_3" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button2() {
  return (
    <div className="h-[28px] relative rounded-[8px] shrink-0 w-[78.359px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <Icon4 />
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[48.5px] not-italic text-[#90a1b9] text-[12px] text-center top-[6.5px] whitespace-nowrap">Enrich</p>
      </div>
    </div>
  );
}

function Icon5() {
  return (
    <div className="absolute left-[12px] size-[12px] top-[8px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g clipPath="url(#clip0_21_2018)" id="Icon">
          <path d={svgPaths.p23551518} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d="M4.5 5.5L6 7L11 2" id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_21_2018">
            <rect fill="white" height="12" style={{ fill: "white", fillOpacity: "1" }} width="12" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Button3() {
  return (
    <div className="flex-[1_0_0] h-[28px] min-h-px min-w-px relative rounded-[8px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <Icon5 />
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[53.5px] not-italic text-[#90a1b9] text-[12px] text-center top-[6.5px] whitespace-nowrap">Validate</p>
      </div>
    </div>
  );
}

function Icon6() {
  return (
    <div className="absolute left-[12px] size-[12px] top-[8px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d={svgPaths.p18b01700} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d="M7.5 2.882V10.382" id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d="M4.5 1.618V9.118" id="Vector_3" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button4() {
  return (
    <div className="h-[28px] relative rounded-[8px] shrink-0 w-[67.188px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <Icon6 />
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[43px] not-italic text-[#90a1b9] text-[12px] text-center top-[6.5px] whitespace-nowrap">Map</p>
      </div>
    </div>
  );
}

function Icon7() {
  return (
    <div className="absolute left-[12px] size-[12px] top-[8px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 12 12">
        <g id="Icon">
          <path d={svgPaths.p334c67c0} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d={svgPaths.p3ce34180} id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d="M4.5 7L5.5 8L7.5 6" id="Vector_3" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Button5() {
  return (
    <div className="h-[28px] relative rounded-[8px] shrink-0 w-[83.148px]" data-name="Button">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <Icon7 />
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[16px] left-[51px] not-italic text-[#90a1b9] text-[12px] text-center top-[6.5px] whitespace-nowrap">Review</p>
      </div>
    </div>
  );
}

function Container8() {
  return (
    <div className="absolute bg-[#f1f5f9] content-stretch flex gap-[4px] h-[36px] items-center left-[371.07px] px-[4px] rounded-[10px] top-[9.5px] w-[423.93px]" data-name="Container">
      <Button1 />
      <Button2 />
      <Button3 />
      <Button4 />
      <Button5 />
    </div>
  );
}

function Icon8() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g clipPath="url(#clip0_21_2008)" id="Icon">
          <path d={svgPaths.p39ee6532} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d={svgPaths.p11f26280} id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d="M8 11.3333H8.00667" id="Vector_3" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
        <defs>
          <clipPath id="clip0_21_2008">
            <rect fill="white" height="16" style={{ fill: "white", fillOpacity: "1" }} width="16" />
          </clipPath>
        </defs>
      </svg>
    </div>
  );
}

function Button6() {
  return (
    <div className="absolute content-stretch flex items-center justify-center left-0 px-[8px] rounded-[10px] size-[32px] top-0" data-name="Button">
      <Icon8 />
    </div>
  );
}

function Icon9() {
  return (
    <div className="absolute left-[8px] size-[16px] top-[8px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 16 16">
        <g id="Icon">
          <path d={svgPaths.p1ce3c700} id="Vector" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
          <path d={svgPaths.p1a06de00} id="Vector_2" stroke="var(--stroke-0, #90A1B9)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.33333" style={{ stroke: "color(display-p3 0.5647 0.6314 0.7255)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Text6() {
  return <div className="absolute bg-[#00bc7d] left-[18px] rounded-[16777200px] size-[8px] top-[6px]" data-name="Text" />;
}

function Button7() {
  return (
    <div className="absolute left-[40px] rounded-[10px] size-[32px] top-0" data-name="Button">
      <Icon9 />
      <Text6 />
    </div>
  );
}

function Container9() {
  return (
    <div className="absolute h-[32px] left-[811px] top-[11.5px] w-[72px]" data-name="Container">
      <Button6 />
      <Button7 />
    </div>
  );
}

function Layout1() {
  return (
    <div className="absolute bg-[rgba(255,255,255,0.8)] border-[#e2e8f0] border-b border-solid h-[56px] left-0 top-0 w-[899px]" data-name="Layout">
      <Button />
      <Container7 />
      <Container8 />
      <Container9 />
    </div>
  );
}

export default function DocumentUploadPage() {
  return (
    <div className="bg-white relative size-full" data-name="Document Upload_Page">
      <Layout />
      <Layout1 />
    </div>
  );
}