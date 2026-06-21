import React from 'react'
import PropTypes from 'prop-types'

export const LoadingSpinner = ({ size = 'md', color = 'blue', centered = true }) => {
  const sizeMap = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-[3px]',
    lg: 'h-12 w-12 border-4',
  }

  // Dynamically mapping tailwind arbitrary colors is tricky, using raw style or pre-mapped colors
  const colorMap = {
    blue: 'border-blue-500',
    red: 'border-red-500',
    green: 'border-green-500',
    white: 'border-white',
  }

  const borderClass = colorMap[color] || 'border-blue-500'
  const sizeClass = sizeMap[size] || sizeMap.md

  const spinner = (
    <div
      className={`animate-spin rounded-full border-t-transparent border-r-transparent ${borderClass} ${sizeClass}`}
    ></div>
  )

  if (centered) {
    return (
      <div className="flex justify-center items-center w-full h-full min-h-[100px]">{spinner}</div>
    )
  }
  return spinner
}

LoadingSpinner.propTypes = {
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  color: PropTypes.oneOf(['blue', 'red', 'green', 'white']),
  centered: PropTypes.bool,
}
