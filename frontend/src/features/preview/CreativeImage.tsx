import { ImageOff } from 'lucide-react'
import { useState, type CSSProperties } from 'react'
import { isHttpsUrl } from './creativeStyle'

interface CreativeImageProps {
  url?: string
  className?: string
  style?: CSSProperties
}

// Ссылки в моках ведут на несуществующий домен, поэтому заглушка здесь обычный случай, а не авария.
export function CreativeImage({ url, className, style }: CreativeImageProps) {
  const [failedUrl, setFailedUrl] = useState<string>()

  if (!isHttpsUrl(url) || failedUrl === url) {
    return (
      <div
        role="img"
        aria-label="Изображение недоступно"
        className={`flex items-center justify-center bg-black/10 text-black/50 ${className ?? ''}`}
        style={style}
      >
        <ImageOff className="size-6" aria-hidden="true" />
      </div>
    )
  }

  return <img src={url} alt="" className={`bg-black/10 object-cover ${className ?? ''}`} style={style} onError={() => setFailedUrl(url)} />
}
