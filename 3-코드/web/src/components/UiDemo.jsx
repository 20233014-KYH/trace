// UI 라이브러리 연결 확인 — shadcn/ui · Magic UI · React Bits 세 곳에서 가져온 부품이 한 화면에서 도는지.
// 헤더의 [UI 데모] 로 열린다. 실제 화면에 쓸 부품은 여기서 골라 SessionView/LearnView 에 옮긴다.
import { Button } from '@/components/ui/button';               // shadcn/ui
import { ShimmerButton } from '@/components/ui/shimmer-button'; // Magic UI
import { NumberTicker } from '@/components/ui/number-ticker';   // Magic UI
import BlurText from '@/components/BlurText';                   // React Bits

export default function UiDemo() {
  return (
    <div className="mx-auto max-w-3xl py-10 space-y-10">
      <section className="space-y-2">
        <p className="text-sm text-muted-foreground">React Bits · BlurText</p>
        <BlurText text="결과만 남는 작업에서, 과정을 남긴다." delay={80} animateBy="words" className="text-3xl font-bold tracking-tight" />
      </section>

      <section className="space-y-2">
        <p className="text-sm text-muted-foreground">Magic UI · NumberTicker (한눈에 두 숫자에 쓸 수 있음)</p>
        <div className="flex gap-12">
          <div><div className="text-sm text-muted-foreground">직접 입력</div><div className="text-5xl font-bold tracking-tight"><NumberTicker value={42} />%</div></div>
          <div><div className="text-sm text-muted-foreground">붙여넣기</div><div className="text-5xl font-bold tracking-tight"><NumberTicker value={58} delay={0.2} />%</div></div>
          <div><div className="text-sm text-muted-foreground">이벤트</div><div className="text-5xl font-bold tracking-tight"><NumberTicker value={1287} delay={0.4} /></div></div>
        </div>
      </section>

      <section className="space-y-2">
        <p className="text-sm text-muted-foreground">shadcn/ui · Button 변형 + Magic UI · ShimmerButton</p>
        <div className="flex flex-wrap items-center gap-3">
          <Button>세션 시작</Button>
          <Button variant="outline">검증 파일</Button>
          <Button variant="secondary">체인 원본</Button>
          <Button variant="ghost">취소</Button>
          <ShimmerButton className="text-sm">증명서 만들기</ShimmerButton>
        </div>
      </section>

      <p className="text-xs text-muted-foreground border-t pt-4">
        가져오는 법: <code className="font-mono">npx shadcn@latest add button</code> · <code className="font-mono">npx shadcn@latest add @magicui/shimmer-button</code> · <code className="font-mono">npx shadcn@latest add @react-bits/BlurText-JS-TW</code>
      </p>
    </div>
  );
}
