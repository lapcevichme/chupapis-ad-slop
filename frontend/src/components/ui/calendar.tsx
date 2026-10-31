import type { ComponentProps } from 'react'
import { DayPicker } from 'react-day-picker'
import { ru } from 'react-day-picker/locale'

const NAV_BUTTON_CLASS =
  'flex size-11 cursor-pointer items-center justify-center rounded-md outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-40 [&_svg]:size-4 [&_svg]:fill-current'

export function Calendar(props: ComponentProps<typeof DayPicker>) {
  return (
    <DayPicker
      locale={ru}
      showOutsideDays
      classNames={{
        months: 'relative',
        nav: 'absolute inset-x-0 top-0 flex justify-between',
        button_previous: NAV_BUTTON_CLASS,
        button_next: NAV_BUTTON_CLASS,
        month_caption: 'flex h-11 items-center justify-center',
        caption_label: 'inline-block text-sm leading-5 font-semibold first-letter:uppercase',
        month_grid: 'border-collapse',
        weekday: 'h-8 text-xs leading-4 font-normal text-muted-foreground',
        day: 'p-0 text-center',
        day_button:
          'size-11 cursor-pointer rounded-md text-sm leading-5 tabular-nums outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed',
        // Сегодняшний день и выбранный отличаются не только цветом: подчёркивание и заливка всей ячейки.
        today: 'font-semibold [&>button]:underline [&>button]:underline-offset-4',
        selected: 'font-semibold [&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:hover:bg-primary',
        outside: 'text-muted-foreground',
        disabled: 'opacity-40 [&>button]:line-through',
      }}
      {...props}
    />
  )
}
