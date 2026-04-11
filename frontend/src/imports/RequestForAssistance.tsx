import svgPaths from "./svg-uop3xjefbu";

function Heading1() {
  return (
    <div className="h-[36px] relative shrink-0 w-full" data-name="Heading 2">
      <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[36px] left-[336.4px] not-italic text-[#101828] text-[30px] text-center top-[-1.78px] whitespace-nowrap">Upload Supplier Data</p>
    </div>
  );
}

function Paragraph() {
  return (
    <div className="h-[48px] relative shrink-0 w-full" data-name="Paragraph">
      <p className="-translate-x-1/2 absolute font-['Inter:Regular',sans-serif] font-normal leading-[24px] left-[336.21px] not-italic text-[#4a5565] text-[16px] text-center top-[-2.11px] w-[633px]">Upload a CSV file containing supplier information to begin biodiversity risk screening. The system will infer locations, enrich data via ABN lookup, and assess environmental risk.</p>
    </div>
  );
}

function Container() {
  return (
    <div className="content-stretch flex flex-col gap-[12px] h-[96px] items-start relative shrink-0 w-full" data-name="Container">
      <Heading1 />
      <Paragraph />
    </div>
  );
}

function Icon() {
  return (
    <div className="absolute left-[312px] size-[48px] top-[49.78px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 48 48">
        <g id="Icon">
          <path d={svgPaths.p38375ec0} id="Vector" stroke="var(--stroke-0, #99A1AF)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" style={{ stroke: "color(display-p3 0.6000 0.6314 0.6863)", strokeOpacity: "1" }} />
          <path d="M34 16L24 6L14 16" id="Vector_2" stroke="var(--stroke-0, #99A1AF)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" style={{ stroke: "color(display-p3 0.6000 0.6314 0.6863)", strokeOpacity: "1" }} />
          <path d="M24 6V30" id="Vector_3" stroke="var(--stroke-0, #99A1AF)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" style={{ stroke: "color(display-p3 0.6000 0.6314 0.6863)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Paragraph1() {
  return (
    <div className="absolute h-[24px] left-[49.78px] top-[113.78px] w-[572.444px]" data-name="Paragraph">
      <p className="-translate-x-1/2 absolute font-['Inter:Regular',sans-serif] font-normal leading-[24px] left-[286.07px] not-italic text-[#364153] text-[16px] text-center top-[-2.11px] whitespace-nowrap">Drag and drop your supplier CSV file here</p>
    </div>
  );
}

function Paragraph2() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-[49.78px] top-[145.78px] w-[572.444px]" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[20px] min-h-px min-w-px not-italic relative text-[#6a7282] text-[14px] text-center">or click to browse</p>
    </div>
  );
}

function Label() {
  return (
    <div className="absolute bg-[#155dfc] h-[40px] left-[275.75px] rounded-[10px] top-[181.78px] w-[120.5px]" data-name="Label">
      <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-[60px] not-italic text-[16px] text-center text-white top-[5.89px] whitespace-nowrap">Select File</p>
    </div>
  );
}

function Paragraph3() {
  return (
    <div className="absolute content-stretch flex h-[15.986px] items-start left-[49.78px] top-[237.78px] w-[572.444px]" data-name="Paragraph">
      <p className="flex-[1_0_0] font-['Inter:Regular',sans-serif] font-normal leading-[16px] min-h-px min-w-px not-italic relative text-[#99a1af] text-[12px] text-center">Supported format: CSV with supplier name, ABN, address, commodity</p>
    </div>
  );
}

function FileUpload() {
  return (
    <div className="bg-white h-[303.542px] relative rounded-[10px] shrink-0 w-full" data-name="FileUpload">
      <div aria-hidden="true" className="absolute border-[#d1d5dc] border-[1.778px] border-dashed inset-0 pointer-events-none rounded-[10px]" />
      <Icon />
      <Paragraph1 />
      <Paragraph2 />
      <Label />
      <Paragraph3 />
    </div>
  );
}

function Heading2() {
  return (
    <div className="h-[28px] relative shrink-0 w-full" data-name="Heading 3">
      <p className="absolute font-['Inter:Medium',sans-serif] font-medium leading-[28px] left-0 not-italic text-[#1c398e] text-[18px] top-[-1.22px] whitespace-nowrap">What happens next:</p>
    </div>
  );
}

function Text() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-0 top-[2px] w-[5.694px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#155dfc] text-[14px] whitespace-nowrap">•</p>
    </div>
  );
}

function Text1() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-[13.69px] top-0 w-[363.597px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#193cb8] text-[14px] whitespace-nowrap">Location inference from uploaded addresses and ABN data</p>
    </div>
  );
}

function ListItem() {
  return (
    <div className="h-[22px] relative shrink-0 w-full" data-name="List Item">
      <Text />
      <Text1 />
    </div>
  );
}

function Text2() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-0 top-[2px] w-[5.694px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#155dfc] text-[14px] whitespace-nowrap">•</p>
    </div>
  );
}

function Text3() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-[13.69px] top-0 w-[344.264px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#193cb8] text-[14px] whitespace-nowrap">ABN enrichment via Australian Business Register lookup</p>
    </div>
  );
}

function ListItem1() {
  return (
    <div className="h-[22px] relative shrink-0 w-full" data-name="List Item">
      <Text2 />
      <Text3 />
    </div>
  );
}

function Text4() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-0 top-[2px] w-[5.694px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#155dfc] text-[14px] whitespace-nowrap">•</p>
    </div>
  );
}

function Text5() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-[13.69px] top-0 w-[470.347px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#193cb8] text-[14px] whitespace-nowrap">Biodiversity GIS overlay against protected areas and threatened species data</p>
    </div>
  );
}

function ListItem2() {
  return (
    <div className="h-[22px] relative shrink-0 w-full" data-name="List Item">
      <Text4 />
      <Text5 />
    </div>
  );
}

function Text6() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-0 top-[2px] w-[5.694px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#155dfc] text-[14px] whitespace-nowrap">•</p>
    </div>
  );
}

function Text7() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-start left-[13.69px] top-0 w-[353.319px]" data-name="Text">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#193cb8] text-[14px] whitespace-nowrap">Risk scoring and confidence assessment for each supplier</p>
    </div>
  );
}

function ListItem3() {
  return (
    <div className="h-[22px] relative shrink-0 w-full" data-name="List Item">
      <Text6 />
      <Text7 />
    </div>
  );
}

function List() {
  return (
    <div className="content-stretch flex flex-col gap-[8px] h-[112px] items-start relative shrink-0 w-full" data-name="List">
      <ListItem />
      <ListItem1 />
      <ListItem2 />
      <ListItem3 />
    </div>
  );
}

function Container1() {
  return (
    <div className="bg-[#eff6ff] h-[201.778px] relative rounded-[10px] shrink-0 w-full" data-name="Container">
      <div aria-hidden="true" className="absolute border-[#bedbff] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="content-stretch flex flex-col gap-[12px] items-start pb-[0.889px] pt-[24.889px] px-[24.889px] relative size-full">
        <Heading2 />
        <List />
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="absolute bg-[#f9fafb] content-stretch flex flex-col gap-[32px] h-[665.319px] items-start left-[337.33px] top-[116.88px] w-[672px]" data-name="App">
      <Container />
      <FileUpload />
      <Container1 />
    </div>
  );
}

function Icon1() {
  return (
    <div className="h-[28px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <div className="absolute inset-[8.33%_12.5%_16.67%_16.58%]" data-name="Vector">
        <div className="absolute inset-[-5.56%_-5.88%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 22.1914 23.3334">
            <path d={svgPaths.p2ed52800} id="Vector" stroke="var(--stroke-0, #008236)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.33333" style={{ stroke: "color(display-p3 0.0000 0.5098 0.2118)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
      <div className="absolute bottom-[12.5%] left-[8.33%] right-[45.83%] top-1/2" data-name="Vector">
        <div className="absolute inset-[-11.11%_-9.09%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 15.1667 12.8333">
            <path d={svgPaths.p13e0c8c0} id="Vector" stroke="var(--stroke-0, #008236)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.33333" style={{ stroke: "color(display-p3 0.0000 0.5098 0.2118)", strokeOpacity: "1" }} />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Container4() {
  return (
    <div className="bg-[#dcfce7] relative rounded-[10px] shrink-0 size-[44px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start pt-[8px] px-[8px] relative size-full">
        <Icon1 />
      </div>
    </div>
  );
}

function Heading() {
  return (
    <div className="content-stretch flex h-[31.986px] items-start relative shrink-0 w-full" data-name="Heading 1">
      <p className="flex-[1_0_0] font-['Inter:Medium',sans-serif] font-medium leading-[32px] min-h-px min-w-px not-italic relative text-[#101828] text-[24px]">Biodiversity Risk Screening</p>
    </div>
  );
}

function Paragraph4() {
  return (
    <div className="content-stretch flex h-[20px] items-start relative shrink-0 w-full" data-name="Paragraph">
      <p className="font-['Inter:Regular',sans-serif] font-normal leading-[20px] not-italic relative shrink-0 text-[#6a7282] text-[14px] whitespace-nowrap">Supplier location inference and biodiversity risk assessment</p>
    </div>
  );
}

function Container5() {
  return (
    <div className="h-[51.986px] relative shrink-0 w-[366.069px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex flex-col items-start relative size-full">
        <Heading />
        <Paragraph4 />
      </div>
    </div>
  );
}

function Container3() {
  return (
    <div className="h-[51.986px] relative shrink-0 w-[422.069px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[12px] items-center relative size-full">
        <Container4 />
        <Container5 />
      </div>
    </div>
  );
}

function Icon2() {
  return (
    <div className="relative shrink-0 size-[18px]" data-name="Icon">
      <svg className="absolute block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 18 18">
        <g id="Icon">
          <path d={svgPaths.pb56cd00} id="Vector" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
          <path d={svgPaths.pdd08040} id="Vector_2" stroke="var(--stroke-0, #0A0A0A)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" style={{ stroke: "color(display-p3 0.0392 0.0392 0.0392)", strokeOpacity: "1" }} />
        </g>
      </svg>
    </div>
  );
}

function Text8() {
  return (
    <div className="h-[24px] relative shrink-0 w-[44px]" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid relative size-full">
        <p className="-translate-x-1/2 absolute font-['Inter:Medium',sans-serif] font-medium leading-[24px] left-[22px] not-italic text-[#0a0a0a] text-[16px] text-center top-[-2.11px] whitespace-nowrap">Home</p>
      </div>
    </div>
  );
}

function Button() {
  return (
    <div className="flex-[1_0_0] h-[41.778px] min-h-px min-w-px relative rounded-[10px]" data-name="Button">
      <div aria-hidden="true" className="absolute border-[#d1d5dc] border-[0.889px] border-solid inset-0 pointer-events-none rounded-[10px]" />
      <div className="flex flex-row items-center size-full">
        <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center pl-[16.889px] pr-[0.889px] py-[0.889px] relative size-full">
          <Icon2 />
          <Text8 />
        </div>
      </div>
    </div>
  );
}

function Container6() {
  return (
    <div className="h-[41.778px] relative shrink-0 w-[103.778px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-center relative size-full">
        <Button />
      </div>
    </div>
  );
}

function Container2() {
  return (
    <div className="h-[51.986px] relative shrink-0 w-full" data-name="Container">
      <div className="flex flex-row items-center size-full">
        <div className="content-stretch flex items-center justify-between relative size-full">
          <Container3 />
          <Container6 />
        </div>
      </div>
    </div>
  );
}

function App1() {
  return (
    <div className="absolute bg-white content-stretch flex flex-col h-[84.875px] items-start left-0 pb-[0.889px] pt-[16px] px-[57.333px] top-0 w-[1346.667px]" data-name="App">
      <div aria-hidden="true" className="absolute border-[#e5e7eb] border-b-[0.889px] border-solid inset-0 pointer-events-none" />
      <Container2 />
    </div>
  );
}

export default function RequestForAssistance() {
  return (
    <div className="bg-white relative size-full" data-name="Request for Assistance">
      <App />
      <App1 />
    </div>
  );
}